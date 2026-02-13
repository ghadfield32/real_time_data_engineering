
  
    
    
      
    

    create  table
      "dev"."main"."dim_dates__dbt_tmp"
  
  (
    date_key date,
    year bigint,
    month bigint,
    day_of_month bigint,
    day_of_week_num bigint,
    day_of_week_name varchar,
    month_name varchar,
    week_of_year bigint,
    is_weekend boolean,
    is_holiday boolean
    
    )
 ;
    insert into "dev"."main"."dim_dates__dbt_tmp" 
  (
    
      
      date_key ,
    
      
      year ,
    
      
      month ,
    
      
      day_of_month ,
    
      
      day_of_week_num ,
    
      
      day_of_week_name ,
    
      
      month_name ,
    
      
      week_of_year ,
    
      
      is_weekend ,
    
      
      is_holiday 
    
  )
 (
      
    select date_key, year, month, day_of_month, day_of_week_num, day_of_week_name, month_name, week_of_year, is_weekend, is_holiday
    from (
        /*
    Dimension table: Calendar dates for January 2024.
    Uses adapter-dispatched macros for dayname/monthname.
*/

with date_spine as (
    





with rawdata as (

    

    

    with p as (
        select 0 as generated_number union all select 1
    ), unioned as (

    select

    
    p0.generated_number * power(2, 0)
     + 
    
    p1.generated_number * power(2, 1)
     + 
    
    p2.generated_number * power(2, 2)
     + 
    
    p3.generated_number * power(2, 3)
     + 
    
    p4.generated_number * power(2, 4)
    
    
    + 1
    as generated_number

    from

    
    p as p0
     cross join 
    
    p as p1
     cross join 
    
    p as p2
     cross join 
    
    p as p3
     cross join 
    
    p as p4
    
    

    )

    select *
    from unioned
    where generated_number <= 31
    order by generated_number



),

all_periods as (

    select (
        

    date_add(cast('2024-01-01' as date), interval (row_number() over (order by generated_number) - 1) day)


    ) as date_day
    from rawdata

),

filtered as (

    select *
    from all_periods
    where date_day <= cast('2024-02-01' as date)

)

select * from filtered


),

final as (
    select
        cast(date_day as date) as date_key,
        extract(year from date_day) as year,
        extract(month from date_day) as month,
        extract(day from date_day) as day_of_month,
        extract(dow from date_day) as day_of_week_num,
        
    dayname(date_day)
 as day_of_week_name,
        
    monthname(date_day)
 as month_name,
        extract(week from date_day) as week_of_year,
        case
            when extract(dow from date_day) in (0, 6) then true
            else false
        end as is_weekend,
        case
            when cast(date_day as date) in (
                cast('2024-01-01' as date),
                cast('2024-01-15' as date)
            ) then true
            else false
        end as is_holiday

    from date_spine
)

select * from final
    ) as model_subq
    );
  
  