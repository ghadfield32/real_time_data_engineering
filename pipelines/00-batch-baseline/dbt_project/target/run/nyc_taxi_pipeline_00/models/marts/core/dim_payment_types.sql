
  
    
    
      
    

    create  table
      "dev"."main"."dim_payment_types__dbt_tmp"
  
  (
    payment_type_id integer,
    payment_type_name varchar
    
    )
 ;
    insert into "dev"."main"."dim_payment_types__dbt_tmp" 
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
    select * from "dev"."main"."stg_payment_types"
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
  
  