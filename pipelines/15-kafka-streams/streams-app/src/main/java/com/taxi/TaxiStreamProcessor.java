package com.taxi;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.gson.JsonElement;
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.streams.*;
import org.apache.kafka.streams.kstream.*;

import java.security.MessageDigest;
import java.time.Duration;
import java.util.Properties;
import java.util.concurrent.CountDownLatch;

public class TaxiStreamProcessor {

    private static final Gson gson = new Gson();

    public static void main(String[] args) {
        String bootstrapServers = System.getenv().getOrDefault("BOOTSTRAP_SERVERS", "kafka:9092");
        String inputTopic = System.getenv().getOrDefault("INPUT_TOPIC", "taxi.raw_trips");
        String bronzeTopic = System.getenv().getOrDefault("BRONZE_TOPIC", "taxi.bronze");
        String silverTopic = System.getenv().getOrDefault("SILVER_TOPIC", "taxi.silver");
        String applicationId = System.getenv().getOrDefault("APPLICATION_ID", "p15-taxi-processor");

        Properties props = new Properties();
        props.put(StreamsConfig.APPLICATION_ID_CONFIG, applicationId);
        props.put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put(StreamsConfig.DEFAULT_KEY_SERDE_CLASS_CONFIG, Serdes.String().getClass().getName());
        props.put(StreamsConfig.DEFAULT_VALUE_SERDE_CLASS_CONFIG, Serdes.String().getClass().getName());
        props.put(StreamsConfig.COMMIT_INTERVAL_MS_CONFIG, 1000);
        props.put(StreamsConfig.NUM_STREAM_THREADS_CONFIG, 2);

        StreamsBuilder builder = new StreamsBuilder();

        // Read raw events from input topic
        KStream<String, String> rawStream = builder.stream(inputTopic);

        // Bronze: Parse JSON, rename fields, write to bronze topic
        KStream<String, String> bronzeStream = rawStream.mapValues(value -> {
            try {
                JsonObject raw = gson.fromJson(value, JsonObject.class);
                JsonObject bronze = new JsonObject();

                bronze.addProperty("vendor_id", getInt(raw, "VendorID"));
                bronze.addProperty("pickup_datetime", getString(raw, "tpep_pickup_datetime"));
                bronze.addProperty("dropoff_datetime", getString(raw, "tpep_dropoff_datetime"));
                bronze.addProperty("passenger_count", getDouble(raw, "passenger_count"));
                bronze.addProperty("trip_distance", getDouble(raw, "trip_distance"));
                bronze.addProperty("rate_code_id", getInt(raw, "RatecodeID"));
                bronze.addProperty("store_and_fwd_flag", getString(raw, "store_and_fwd_flag"));
                bronze.addProperty("pickup_location_id", getInt(raw, "PULocationID"));
                bronze.addProperty("dropoff_location_id", getInt(raw, "DOLocationID"));
                bronze.addProperty("payment_type", getInt(raw, "payment_type"));
                bronze.addProperty("fare_amount", getDouble(raw, "fare_amount"));
                bronze.addProperty("extra", getDouble(raw, "extra"));
                bronze.addProperty("mta_tax", getDouble(raw, "mta_tax"));
                bronze.addProperty("tip_amount", getDouble(raw, "tip_amount"));
                bronze.addProperty("tolls_amount", getDouble(raw, "tolls_amount"));
                bronze.addProperty("improvement_surcharge", getDouble(raw, "improvement_surcharge"));
                bronze.addProperty("total_amount", getDouble(raw, "total_amount"));
                bronze.addProperty("congestion_surcharge", getDouble(raw, "congestion_surcharge"));
                bronze.addProperty("airport_fee", getDouble(raw, "Airport_fee"));

                return gson.toJson(bronze);
            } catch (Exception e) {
                return null;
            }
        }).filter((key, value) -> value != null);

        bronzeStream.to(bronzeTopic);

        // Silver: Quality filters + computed fields
        KStream<String, String> silverStream = bronzeStream.mapValues(value -> {
            try {
                JsonObject b = gson.fromJson(value, JsonObject.class);

                // Quality filters
                String pickup = b.has("pickup_datetime") && !b.get("pickup_datetime").isJsonNull()
                    ? b.get("pickup_datetime").getAsString() : null;
                String dropoff = b.has("dropoff_datetime") && !b.get("dropoff_datetime").isJsonNull()
                    ? b.get("dropoff_datetime").getAsString() : null;
                double distance = b.has("trip_distance") ? b.get("trip_distance").getAsDouble() : -1;
                double fare = b.has("fare_amount") ? b.get("fare_amount").getAsDouble() : -1;

                if (pickup == null || dropoff == null || distance < 0 || fare < 0) {
                    return null;
                }

                // Generate trip_id
                String tripIdInput = String.join("|",
                    String.valueOf(b.get("vendor_id").getAsInt()),
                    pickup, dropoff,
                    String.valueOf(b.get("pickup_location_id").getAsInt()),
                    String.valueOf(b.get("dropoff_location_id").getAsInt()),
                    String.valueOf(fare),
                    String.valueOf(b.get("total_amount").getAsDouble())
                );
                b.addProperty("trip_id", md5(tripIdInput));

                return gson.toJson(b);
            } catch (Exception e) {
                return null;
            }
        }).filter((key, value) -> value != null);

        silverStream.to(silverTopic);

        // Build and start the topology
        Topology topology = builder.build();
        System.out.println("Topology:\n" + topology.describe());

        KafkaStreams streams = new KafkaStreams(topology, props);

        final CountDownLatch latch = new CountDownLatch(1);
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            streams.close(Duration.ofSeconds(10));
            latch.countDown();
        }));

        try {
            streams.start();
            System.out.println("Kafka Streams application started.");
            System.out.println("Processing: " + inputTopic + " -> " + bronzeTopic + " -> " + silverTopic);
            latch.await();
        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
            System.exit(1);
        }
    }

    private static int getInt(JsonObject obj, String key) {
        JsonElement el = obj.get(key);
        if (el == null || el.isJsonNull()) return 0;
        return el.getAsInt();
    }

    private static double getDouble(JsonObject obj, String key) {
        JsonElement el = obj.get(key);
        if (el == null || el.isJsonNull()) return 0.0;
        return el.getAsDouble();
    }

    private static String getString(JsonObject obj, String key) {
        JsonElement el = obj.get(key);
        if (el == null || el.isJsonNull()) return "";
        return el.getAsString();
    }

    private static String md5(String input) {
        try {
            MessageDigest md = MessageDigest.getInstance("MD5");
            byte[] digest = md.digest(input.getBytes());
            StringBuilder sb = new StringBuilder();
            for (byte b : digest) {
                sb.append(String.format("%02x", b));
            }
            return sb.toString();
        } catch (Exception e) {
            return input.hashCode() + "";
        }
    }
}
