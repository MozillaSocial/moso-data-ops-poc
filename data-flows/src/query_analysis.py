import json
import os
import shutil
from pathlib import Path

import duckdb
import snowflake.connector as sfc
from prefect import flow, task
from common.databases.snowflake_utils import MozSnowflakeConnector
from prefect_dask import DaskTaskRunner
# from cryptography.hazmat.backends import default_backend
# from cryptography.hazmat.primitives import serialization
from sqlglot import errors as sqlglot_errors
from sqlglot import exp, parse_one

RESULTS_FILE_PATH = Path("/tmp/query_analysis")


def create_object_name(elements, default_database_name, default_schema_name):
    schema_name = default_schema_name
    database_name = default_database_name
    if elements[0]:
        database_name = elements[0]
    if elements[1]:
        schema_name = elements[1]
    object_name = elements[2]
    return ".".join([database_name, schema_name, object_name]).strip("'").strip('"')


def process_query(row):
    try:
        results = parse_one(row["QUERY_TEXT"], dialect="snowflake").find_all(exp.Table)
    except sqlglot_errors.ParseError:
        return {
            "object_affected": "Cannot Parse",
            "start_date": row["START_TIME"].strftime("%m/%d/%Y"),
            "query_cost": float(row["QUERY_COST"]),
        }
    object_affected_raw = [[t.catalog, t.db, t.name] for t in results][0]
    object_affected = create_object_name(
        object_affected_raw,
        row["DATABASE_NAME"],
        row["SCHEMA_NAME"],
    )
    return {
        "object_affected": object_affected,
        "start_date": row["START_TIME"].strftime("%m/%d/%Y"),
        "query_cost": float(row["QUERY_COST"]),
    }


@task()
def process_batch(batch, batch_num):
    data = list(map(process_query, batch))
    with open(os.path.join(RESULTS_FILE_PATH, f"data_{batch_num}.json"), "w") as f:
        json.dump(data, f)


@task()
def get_batches():
    # with open("/Users/mozilla/.snowflake-keys/rsa_key.p8", "rb") as key:
    #     p_key = serialization.load_pem_private_key(
    #         key.read(),
    #         password=os.environ["PRIVATE_KEY_PASSPHRASE"].encode(),
    #         backend=default_backend(),
    #     )

    # pkb = p_key.private_bytes(
    #     encoding=serialization.Encoding.DER,
    #     format=serialization.PrivateFormat.PKCS8,
    #     encryption_algorithm=serialization.NoEncryption(),
    # )

    # with sfc.connect(connection_name="snowflake_local", private_key=pkb) as conn:
    with MozSnowflakeConnector().get_connection() as conn:
        with conn.cursor(sfc.DictCursor) as cur:
            cur.execute(
                """select query_text, 
                    start_time, 
                    query_cost,
                    database_name,
                    schema_name
                    from development.braun.query_usage_history
                    where query_type in (
                        'CREATE_TABLE_AS_SELECT',
                        'INSERT',
                        'MERGE',
                        'UPDATE',
                        'DELETE'
                        )"""
            )
            return cur.get_result_batches()


@task()
def output_analysis():
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
                order by query_cost desc
            ) 
            TO 'output.csv' (HEADER, DELIMITER ',')"""
    )


@flow(task_runner=DaskTaskRunner(cluster_kwargs={"n_workers": 4}))
# @flow
def main():
    shutil.rmtree(RESULTS_FILE_PATH)
    RESULTS_FILE_PATH.mkdir(exist_ok=True)
    batches = get_batches()
    # results = [
    #     process_batch(batch, idx)
    #     for idx, batch in enumerate(batches)
    #     if batch.rowcount > 0
    # ]
    jobs = []
    for idx, batch in enumerate(batches):  # type: ignore
        if batch.rowcount > 0:
            process_batch.submit(batch, idx)
            jobs.append(process_batch.submit(batch, idx))
    results = [x.result() for x in jobs]
    # output_analysis()  # type: ignore
    output_analysis(wait_for=[results])  # type: ignore


if __name__ == "__main__":
    main()
