"""Metrics collection for pipeline benchmarking.

Collects Docker container stats (CPU, memory) and timing data
for each pipeline run.
"""

import subprocess
import time
import threading
from dataclasses import dataclass, field


@dataclass
class PipelineMetrics:
    """Collected metrics for a single pipeline benchmark run."""
    pipeline_id: str
    pipeline_name: str

    # Timing
    startup_time_s: float = 0.0
    ingestion_time_s: float = 0.0
    processing_time_s: float = 0.0
    dbt_build_time_s: float = 0.0
    total_e2e_time_s: float = 0.0

    # Throughput
    events_produced: int = 0
    events_per_second: float = 0.0

    # Resources (peak across all containers)
    peak_memory_mb: float = 0.0
    peak_cpu_percent: float = 0.0
    avg_memory_mb: float = 0.0
    container_count: int = 0

    # Validation
    row_count_match: bool = False
    accuracy_match: bool = False
    dbt_test_pass: bool = False
    expected_row_count: int = 0
    actual_row_count: int = 0

    # Per-container breakdown
    container_stats: dict = field(default_factory=dict)


class DockerStatsCollector:
    """Background collector for Docker container resource usage."""

    def __init__(self, project_name: str):
        self.project_name = project_name
        self._running = False
        self._thread = None
        self._samples = []

    def start(self):
        self._running = True
        self._samples = []
        self._thread = threading.Thread(target=self._collect_loop, daemon=True)
        self._thread.start()

    def stop(self) -> dict:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        return self._summarize()

    def _collect_loop(self):
        while self._running:
            try:
                result = subprocess.run(
                    ["docker", "stats", "--no-stream", "--format",
                     "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"],
                    capture_output=True, text=True, timeout=10,
                )
                if result.returncode == 0:
                    sample = {}
                    for line in result.stdout.strip().split("\n"):
                        if not line:
                            continue
                        parts = line.split("\t")
                        if len(parts) >= 4:
                            name = parts[0]
                            cpu = float(parts[1].replace("%", ""))
                            mem_str = parts[2].split("/")[0].strip()
                            mem_mb = self._parse_memory(mem_str)
                            sample[name] = {"cpu": cpu, "mem_mb": mem_mb}
                    if sample:
                        self._samples.append(sample)
            except (subprocess.TimeoutExpired, Exception):
                pass
            time.sleep(2)

    @staticmethod
    def _parse_memory(mem_str: str) -> float:
        """Parse Docker memory string like '1.5GiB' or '512MiB' to MB."""
        mem_str = mem_str.strip()
        if "GiB" in mem_str:
            return float(mem_str.replace("GiB", "")) * 1024
        elif "MiB" in mem_str:
            return float(mem_str.replace("MiB", ""))
        elif "KiB" in mem_str:
            return float(mem_str.replace("KiB", "")) / 1024
        elif "GB" in mem_str:
            return float(mem_str.replace("GB", "")) * 1000
        elif "MB" in mem_str:
            return float(mem_str.replace("MB", ""))
        return 0.0

    def _summarize(self) -> dict:
        """Summarize collected samples into peak/avg metrics."""
        if not self._samples:
            return {"peak_memory_mb": 0, "peak_cpu_percent": 0, "avg_memory_mb": 0}

        all_mem = []
        all_cpu = []
        container_peaks = {}

        for sample in self._samples:
            total_mem = sum(s["mem_mb"] for s in sample.values())
            total_cpu = sum(s["cpu"] for s in sample.values())
            all_mem.append(total_mem)
            all_cpu.append(total_cpu)

            for name, stats in sample.items():
                if name not in container_peaks:
                    container_peaks[name] = {"peak_mem_mb": 0, "peak_cpu": 0}
                container_peaks[name]["peak_mem_mb"] = max(
                    container_peaks[name]["peak_mem_mb"], stats["mem_mb"]
                )
                container_peaks[name]["peak_cpu"] = max(
                    container_peaks[name]["peak_cpu"], stats["cpu"]
                )

        return {
            "peak_memory_mb": max(all_mem) if all_mem else 0,
            "peak_cpu_percent": max(all_cpu) if all_cpu else 0,
            "avg_memory_mb": sum(all_mem) / len(all_mem) if all_mem else 0,
            "container_count": len(container_peaks),
            "container_stats": container_peaks,
        }
