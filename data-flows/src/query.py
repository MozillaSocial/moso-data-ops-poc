import duckdb


duckdb.sql(
        """COPY (
                with cte as (
                SELECT 
                    object_affected,
                    start_date,
                    sum(query_cost) as query_cost,
                    count(*) as query_count
                FROM read_json_auto('/tmp/query_analysis/*')
                group by object_affected, start_date
                )
                select object_affected, 
                    avg(query_cost) as avg_query_cost,
                    sum(query_cost) as sum_query_cost,
                    sum(query_count) as query_count
                    from cte
                group by object_affected
                order by sum_query_cost desc
            ) 
            TO 'output.csv' (HEADER, DELIMITER ',')"""
    )