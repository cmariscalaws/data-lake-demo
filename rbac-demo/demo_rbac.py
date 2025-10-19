#!/usr/bin/env python3

"""
RBAC demonstration using Lake Formation with Athena.

This script:
1) Finds the crawler-created table in the Glue database (default: option_a_demo_db).
2) Creates a Lake Formation Data Cells Filter limiting rows to sources ('api-a','api-b') for the core role.
3) Grants Lake Formation permissions:
   - AnalystCoreRole: SELECT via the Data Cells Filter + column-level SELECT on (source, ingestion_date, page, fetched_at)
   - AnalystPiiRole:  Full table SELECT
4) Assumes each role and runs two Athena queries to show the difference.

Usage:
  python scripts/demo_rbac.py --stack OptionAIngestionDemoPyRBAC
"""

import argparse
import json
import time
import boto3

def cf_outputs(stack_name):
    cfn = boto3.client("cloudformation")
    resp = cfn.describe_stacks(StackName=stack_name)["Stacks"][0]
    return {o["OutputKey"]: o["OutputValue"] for o in resp.get("Outputs", [])}

def get_table(db):
    glue = boto3.client("glue")
    tables = glue.get_tables(DatabaseName=db, MaxResults=50)["TableList"]
    if not tables:
        raise SystemExit(f"No tables found in {db}. Run the crawler first.")
    # Prefer table with 'source' and 'ingestion_date' partitions
    for t in tables:
        parts = [p["Name"] for p in t.get("PartitionKeys", [])]
        if "source" in parts and "ingestion_date" in parts:
            return t["Name"]
    return tables[0]["Name"]

def ensure_filter(db, table, name, expr):
    acct = boto3.client("sts").get_caller_identity()["Account"]
    lf = boto3.client("lakeformation")
    try:
        lf.create_data_cells_filter(
            TableData={
                "TableCatalogId": acct,
                "DatabaseName": db,
                "TableName": table,
                "Name": name,
                "RowFilter": {"FilterExpression": expr},
                "ColumnWildcard": {}
            }
        )
        print(f"Created DataCellsFilter {name}: {expr}")
    except lf.exceptions.AlreadyExistsException:
        print(f"DataCellsFilter {name} exists; continuing.")

def grant_core(db, table, role_arn, filter_name, allowed_columns):
    acct = boto3.client("sts").get_caller_identity()["Account"]
    lf = boto3.client("lakeformation")
    # Row-level via filter
    lf.grant_permissions(
        Principal={"DataLakePrincipalIdentifier": role_arn},
        Resource={"DataCellsFilter": {"TableCatalogId": acct, "DatabaseName": db, "TableName": table, "Name": filter_name}},
        Permissions=["SELECT"]
    )
    # Column-level on specific columns
    lf.grant_permissions(
        Principal={"DataLakePrincipalIdentifier": role_arn},
        Resource={"TableWithColumns": {"CatalogId": acct, "DatabaseName": db, "Name": table, "ColumnNames": allowed_columns}},
        Permissions=["SELECT"]
    )
    print(f"Granted core role SELECT with row filter and columns {allowed_columns}")

def grant_pii(db, table, role_arn):
    acct = boto3.client("sts").get_caller_identity()["Account"]
    lf = boto3.client("lakeformation")
    lf.grant_permissions(
        Principal={"DataLakePrincipalIdentifier": role_arn},
        Resource={"Table": {"CatalogId": acct, "DatabaseName": db, "Name": table}},
        Permissions=["SELECT"]
    )
    print("Granted pii role full table SELECT")

def assume(role_arn, session_name):
    sts = boto3.client("sts")
    c = sts.assume_role(RoleArn=role_arn, RoleSessionName=session_name)["Credentials"]
    return boto3.Session(
        aws_access_key_id=c["AccessKeyId"],
        aws_secret_access_key=c["SecretAccessKey"],
        aws_session_token=c["SessionToken"],
        region_name=boto3.Session().region_name,
    )

def athena_query(sess, wg, db, sql):
    ath = sess.client("athena")
    qid = ath.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": db},
        WorkGroup=wg
    )["QueryExecutionId"]
    while True:
        st = ath.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]["State"]
        if st in ("SUCCEEDED","FAILED","CANCELLED"):
            break
        time.sleep(1.0)
    if st != "SUCCEEDED":
        reason = ath.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"].get("StateChangeReason","")
        raise RuntimeError(f"Query failed: {st}: {reason}")
    res = ath.get_query_results(QueryExecutionId=qid)
    cols = [c["Name"] for c in res["ResultSet"]["ResultSetMetadata"]["ColumnInfo"]]
    rows = res["ResultSet"]["Rows"][1:]
    data = [[d.get("VarCharValue") for d in r["Data"]] for r in rows]
    return cols, data

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stack", default="OptionAIngestionDemoPyRBAC")
    ap.add_argument("--db", default=None)
    args = ap.parse_args()

    outs = cf_outputs(args.stack)
    db = args.db or outs.get("GlueDatabaseName","option_a_demo_db")
    
    # Get role ARNs directly since they might not be in CloudFormation outputs
    iam = boto3.client("iam")
    core_role = None
    pii_role = None
    
    # Find the roles by name pattern
    roles = iam.list_roles()["Roles"]
    for role in roles:
        if "AnalystCoreRole" in role["RoleName"]:
            core_role = role["Arn"]
        elif "AnalystPiiRole" in role["RoleName"]:
            pii_role = role["Arn"]
    
    if not core_role or not pii_role:
        raise SystemExit("Could not find AnalystCoreRole or AnalystPiiRole. Make sure Lake Formation RBAC is deployed.")
    
    core_wg = outs.get("AthenaCoreWG","wg_core_read_demo")
    pii_wg = outs.get("AthenaPiiWG","wg_pii_read_demo")

    table = get_table(db)
    print(f"Using table {db}.{table}")

    filter_name = "core_only_a_b"
    ensure_filter(db, table, filter_name, "source in ('api-a','api-b')")

    allowed_columns = ["source","ingestion_date","page","fetched_at"]
    grant_core(db, table, core_role, filter_name, allowed_columns)
    grant_pii(db, table, pii_role)

    # Assume roles and run queries
    core_sess = assume(core_role, "core-demo")
    pii_sess = assume(pii_role, "pii-demo")

    q1 = f'SELECT source, COUNT(*) AS files FROM "{db}"."{table}" GROUP BY 1 ORDER BY 1'
    print("\n[CORE] Expect only api-a and api-b:")
    print(athena_query(core_sess, core_wg, db, q1))

    print("\n[PII] Expect all four sources:")
    print(athena_query(pii_sess, pii_wg, db, q1))

    q2 = f'SELECT source, page, CARDINALITY(items) AS n FROM "{db}"."{table}" ORDER BY source, page LIMIT 5'
    print("\n[CORE] Selecting items (should fail):")
    try:
        print(athena_query(core_sess, core_wg, db, q2))
        print("UNEXPECTED: core was able to read 'items'")
    except Exception as e:
        print(f"Expected failure for core: {e}")

    print("\n[PII] Selecting items (should succeed):")
    print(athena_query(pii_sess, pii_wg, db, q2))

if __name__ == "__main__":
    main()
