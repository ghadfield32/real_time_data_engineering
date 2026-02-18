/*
    RisingWave-compatible view materialization override.

    Problem: dbt-postgres 1.10+ uses a 3-step atomic swap for view creation:
      1. CREATE VIEW model__dbt_tmp AS (...)
      2. DROP VIEW IF EXISTS model
      3. ALTER VIEW model__dbt_tmp RENAME TO model   ← RisingWave fails here

    RisingWave does NOT support:
      - ALTER VIEW ... RENAME TO
      - CREATE OR REPLACE VIEW

    RisingWave DOES support:
      - CREATE VIEW
      - DROP VIEW IF EXISTS

    Fix: Override the postgres view materialization entirely to use
    DROP VIEW IF EXISTS + CREATE VIEW on the target relation directly.
    No __dbt_tmp intermediate, no RENAME needed.
*/

{% macro postgres__create_view_as(relation, sql) -%}
  create view {{ relation }}
    as (
      {{ sql }}
    );
{%- endmacro %}


{% materialization view, adapter='postgres' %}
  {%- set existing_relation = load_cached_relation(this) -%}
  {%- set target_relation = this.incorporate(type='view') -%}
  {%- set grant_config = config.get('grants') -%}

  {{ run_hooks(pre_hooks) }}

  -- Drop existing relation (view or table) to avoid CREATE conflict
  {% if existing_relation is not none %}
    {{ drop_relation_if_exists(existing_relation) }}
  {% endif %}

  -- CREATE VIEW directly on target — no __dbt_tmp intermediate, no RENAME
  {% call statement('main') %}
    {{ create_view_as(target_relation, sql) }}
  {% endcall %}

  {% set should_revoke = should_revoke(existing_relation, full_refresh_mode=False) %}
  {% do apply_grants(target_relation, grant_config, should_revoke=should_revoke) %}

  {% do persist_docs(target_relation, model) %}

  {{ run_hooks(post_hooks) }}

  {{ return({'relations': [target_relation]}) }}
{% endmaterialization %}
