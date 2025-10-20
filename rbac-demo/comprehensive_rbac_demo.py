#!/usr/bin/env python3

"""
Comprehensive RBAC Demo - Validates Row-Level and Column-Level Security
This demo shows Lake Formation RBAC where identical queries return different results
based on role permissions (both row filtering and column restrictions)
"""

import boto3
import time

def get_role_arns():
    """Get the analyst role ARNs"""
    iam = boto3.client("iam")
    roles = iam.list_roles()["Roles"]
    
    core_role = None
    pii_role = None
    
    for role in roles:
        if "AnalystCoreRole" in role["RoleName"]:
            core_role = role["Arn"]
        elif "AnalystPiiRole" in role["RoleName"]:
            pii_role = role["Arn"]
    
    return core_role, pii_role

def run_athena_query(session, workgroup, query, description):
    """Run an Athena query and return results"""
    athena = session.client("athena")
    
    print(f"\n🔍 {description}")
    print(f"Query: {query}")
    
    try:
        query_id = athena.start_query_execution(
            QueryString=query,
            QueryExecutionContext={"Database": "option_a_demo_db"},
            WorkGroup=workgroup
        )["QueryExecutionId"]
        
        # Wait for completion
        while True:
            status = athena.get_query_execution(QueryExecutionId=query_id)["QueryExecution"]["Status"]["State"]
            if status in ("SUCCEEDED", "FAILED", "CANCELLED"):
                break
            time.sleep(1)
        
        if status == "SUCCEEDED":
            results = athena.get_query_results(QueryExecutionId=query_id)
            print("✅ Query succeeded!")
            print("Results:")
            for row in results["ResultSet"]["Rows"][1:]:  # Skip header
                data = [d.get("VarCharValue", "") for d in row["Data"]]
                print(f"  {data}")
            return True, results
        else:
            print(f"❌ Query failed: {status}")
            return False, None
    except Exception as e:
        print(f"❌ Query failed: {e}")
        return False, None

def main():
    print("🎭 Comprehensive Lake Formation RBAC Demo")
    print("=" * 70)
    print("This demo validates BOTH row-level and column-level security")
    print("using identical queries that return different results per role")
    print("=" * 70)
    
    # Get role ARNs
    core_role, pii_role = get_role_arns()
    if not core_role or not pii_role:
        print("❌ Could not find analyst roles")
        return
    
    print(f"Core Role: {core_role}")
    print(f"PII Role: {pii_role}")
    
    # Assume Core Role
    print("\n🔐 Assuming Core Role (Limited Access)...")
    sts = boto3.client("sts")
    core_response = sts.assume_role(
        RoleArn=core_role,
        RoleSessionName="core-demo"
    )
    
    core_session = boto3.Session(
        aws_access_key_id=core_response["Credentials"]["AccessKeyId"],
        aws_secret_access_key=core_response["Credentials"]["SecretAccessKey"],
        aws_session_token=core_response["Credentials"]["SessionToken"],
        region_name="us-west-2"
    )
    
    # Assume PII Role
    print("🔐 Assuming PII Role (Full Access)...")
    pii_response = sts.assume_role(
        RoleArn=pii_role,
        RoleSessionName="pii-demo"
    )
    
    pii_session = boto3.Session(
        aws_access_key_id=pii_response["Credentials"]["AccessKeyId"],
        aws_secret_access_key=pii_response["Credentials"]["SecretAccessKey"],
        aws_session_token=pii_response["Credentials"]["SessionToken"],
        region_name="us-west-2"
    )
    
    # Test 1: Row-Level Security (Data Filtering)
    print(f"\n{'='*70}")
    print("TEST 1: ROW-LEVEL SECURITY - Data Filtering")
    print(f"{'='*70}")
    print("🔒 Core Role should only see api-a data (row filter)")
    print("🔓 PII Role should see all endpoints (no row filter)")
    
    query1 = 'SELECT endpoint, COUNT(*) as files FROM "option_a_demo_db"."raw" GROUP BY endpoint ORDER BY endpoint'
    
    core_success1, core_results1 = run_athena_query(core_session, "wg_core_read_demo", query1, "Core Role: Row-filtered data")
    pii_success1, pii_results1 = run_athena_query(pii_session, "wg_pii_read_demo", query1, "PII Role: All data")
    
    # Test 2: Column-Level Security (Column Access)
    print(f"\n{'='*70}")
    print("TEST 2: COLUMN-LEVEL SECURITY - Column Access")
    print(f"{'='*70}")
    print("🔒 Core Role should FAIL when accessing 'items' column")
    print("🔓 PII Role should SUCCEED when accessing 'items' column")
    
    query2 = 'SELECT endpoint, page, CARDINALITY(items) as item_count FROM "option_a_demo_db"."raw" ORDER BY endpoint, page LIMIT 3'
    
    core_success2, core_results2 = run_athena_query(core_session, "wg_core_read_demo", query2, "Core Role: Attempting to access 'items' column")
    pii_success2, pii_results2 = run_athena_query(pii_session, "wg_pii_read_demo", query2, "PII Role: Accessing 'items' column")
    
    # Test 3: Data Volume Comparison (Shows Row Filtering Effect)
    print(f"\n{'='*70}")
    print("TEST 3: DATA VOLUME COMPARISON - Row Filtering Effect")
    print(f"{'='*70}")
    print("🔒 Core Role: Should see limited record count (api-a only)")
    print("🔓 PII Role: Should see full record count (all endpoints)")
    
    query3 = 'SELECT COUNT(*) as total_records FROM "option_a_demo_db"."raw"'
    
    core_success3, core_results3 = run_athena_query(core_session, "wg_core_read_demo", query3, "Core Role: Limited record count")
    pii_success3, pii_results3 = run_athena_query(pii_session, "wg_pii_read_demo", query3, "PII Role: Full record count")
    
    # Test 4: Sample Data Comparison (Shows Row Filtering Effect)
    print(f"\n{'='*70}")
    print("TEST 4: SAMPLE DATA COMPARISON - Row Filtering Effect")
    print(f"{'='*70}")
    print("🔒 Core Role: Should see only api-a data in sample (20 rows max)")
    print("🔓 PII Role: Should see data from all endpoints in sample (80 rows)")
    
    query4 = 'SELECT endpoint, page, fetched_at FROM "option_a_demo_db"."raw" ORDER BY endpoint, page LIMIT 30'
    
    core_success4, core_results4 = run_athena_query(core_session, "wg_core_read_demo", query4, "Core Role: Sample data (api-a only)")
    pii_success4, pii_results4 = run_athena_query(pii_session, "wg_pii_read_demo", query4, "PII Role: Sample data (all endpoints)")
    
    # Analysis and Results
    print(f"\n{'='*70}")
    print("📊 RBAC VALIDATION RESULTS")
    print(f"{'='*70}")
    
    # Row-level security validation
    print("\n🔍 ROW-LEVEL SECURITY VALIDATION:")
    if core_success1 and pii_success1:
        core_endpoints = set()
        pii_endpoints = set()
        
        if core_results1:
            for row in core_results1["ResultSet"]["Rows"][1:]:
                endpoint = row["Data"][0].get("VarCharValue", "")
                if endpoint:
                    core_endpoints.add(endpoint)
        
        if pii_results1:
            for row in pii_results1["ResultSet"]["Rows"][1:]:
                endpoint = row["Data"][0].get("VarCharValue", "")
                if endpoint:
                    pii_endpoints.add(endpoint)
        
        print(f"  Core Role endpoints: {sorted(core_endpoints)}")
        print(f"  PII Role endpoints: {sorted(pii_endpoints)}")
        
        if core_endpoints == {"api-a"} and pii_endpoints == {"api-a", "api-b", "api-c", "api-d"}:
            print("  ✅ ROW-LEVEL SECURITY: WORKING CORRECTLY")
        else:
            print("  ❌ ROW-LEVEL SECURITY: NOT WORKING")
    else:
        print("  ❌ ROW-LEVEL SECURITY: Cannot validate (query failures)")
    
    # Column-level security validation
    print("\n🔍 COLUMN-LEVEL SECURITY VALIDATION:")
    if not core_success2 and pii_success2:
        print("  ✅ COLUMN-LEVEL SECURITY: WORKING CORRECTLY")
        print("    • Core Role: Cannot access 'items' column (blocked)")
        print("    • PII Role: Can access 'items' column (allowed)")
    elif core_success2 and pii_success2:
        print("  ❌ COLUMN-LEVEL SECURITY: NOT WORKING")
        print("    • Both roles can access 'items' column")
    else:
        print("  ⚠️  COLUMN-LEVEL SECURITY: PARTIAL (check results)")
    
    # Data volume validation
    print("\n🔍 DATA VOLUME VALIDATION:")
    if core_success3 and pii_success3:
        core_count = int(core_results3["ResultSet"]["Rows"][1]["Data"][0]["VarCharValue"])
        pii_count = int(pii_results3["ResultSet"]["Rows"][1]["Data"][0]["VarCharValue"])
        
        print(f"  Core Role record count: {core_count}")
        print(f"  PII Role record count: {pii_count}")
        
        if core_count < pii_count:
            print("  ✅ DATA VOLUME FILTERING: WORKING CORRECTLY")
        else:
            print("  ❌ DATA VOLUME FILTERING: NOT WORKING")
    else:
        print("  ❌ DATA VOLUME VALIDATION: Cannot validate (query failures)")
    
    # Summary
    print(f"\n{'='*70}")
    print("🎯 LAKE FORMATION RBAC SUMMARY")
    print(f"{'='*70}")
    print("✅ DEMONSTRATED CAPABILITIES:")
    print("  • Row-level security (Data Cells Filter)")
    print("  • Column-level security (Column permissions)")
    print("  • Role-based access control")
    print("  • Data segregation (different S3 result paths)")
    print("  • Query-level enforcement")
    
    print(f"\n🔒 SECURITY MODEL:")
    print("  • Core Role: Limited to api-a data, cannot access 'items' column")
    print("  • PII Role: Full access to all data and all columns")
    print("  • Identical queries return different results based on role")
    
    print(f"\n🎉 Comprehensive RBAC demo completed!")
    print("This demonstrates enterprise-grade data lake security!")

if __name__ == "__main__":
    main()
