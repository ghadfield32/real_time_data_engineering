
  
    
    
      
    

    create  table
      "de_pipeline"."main_marts"."dim_payment_types__dbt_tmp"
  
  (
    payment_type_id integer,
    payment_type_name varchar
    
    )
 ;
    insert into "de_pipeline"."main_marts"."dim_payment_types__dbt_tmp" 
  (
    
      
      payment_type_id ,
    
      
      payment_type_name 
    
  )
 (
      
    select payment_type_id, payment_type_name
    from (
        /*
    Dimension table: Payment type descriptions.
*/

with payment_types as (
    select * from "de_pipeline"."main_staging"."stg_payment_types"
),

final as (
    select
        payment_type_id,
        payment_type_name
    from payment_types
)

select * from final
    ) as model_subq
    );
  
  