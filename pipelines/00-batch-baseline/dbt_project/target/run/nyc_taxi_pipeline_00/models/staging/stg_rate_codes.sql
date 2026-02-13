
  
  create view "dev"."main"."stg_rate_codes__dbt_tmp" as (
    /*
    Staging model: Rate code lookup
    Maps rate_code_id to human-readable names.
*/

with source as (
    select * from "dev"."main"."rate_code_lookup"
),

renamed as (
    select
        rate_code_id,
        rate_code_name
    from source
)

select * from renamed
  );
