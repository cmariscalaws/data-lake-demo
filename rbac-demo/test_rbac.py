#!/usr/bin/env python3

"""
Simple test to check Lake Formation RBAC setup
"""

import boto3
import time

def test_role_access(role_arn, role_name, workgroup):
    """Test a specific role's access"""
    print(f"\n🔍 Testing {role_name}...")
    
    try:
        # Assume the role
        sts = boto3.client("sts")
        response = sts.assume_role(
            RoleArn=role_arn,
            RoleSessionName=f"{role_name.lower().replace(' ', '')}-test"
        )
        
        # Create session with assumed role
        session = boto3.Session(
            aws_access_key_id=response["Credentials"]["AccessKeyId"],
            aws_secret_access_key=response["Credentials"]["SecretAccessKey"],
            aws_session_token=response["Credentials"]["SessionToken"],
            region_name="us-west-2"
        )
        
        # Test Athena query
        athena = session.client("athena")
        query_id = athena.start_query_execution(
            QueryString='SELECT source, COUNT(*) as files FROM "option_a_demo_db"."raw" GROUP BY source ORDER BY source',
            QueryExecutionContext={"Database": "option_a_demo_db"},
            WorkGroup=workgroup
        )["QueryExecutionId"]
        
        print(f"  Query ID: {query_id}")
        
        # Wait for completion
        while True:
            status = athena.get_query_execution(QueryExecutionId=query_id)["QueryExecution"]["Status"]["State"]
            if status in ("SUCCEEDED", "FAILED", "CANCELLED"):
                break
            time.sleep(2)
        
        if status == "SUCCEEDED":
            results = athena.get_query_results(QueryExecutionId=query_id)
            print(f"  ✅ {role_name} query succeeded!")
            print("  Results:")
            for row in results["ResultSet"]["Rows"][1:]:  # Skip header
                data = [d.get("VarCharValue", "") for d in row["Data"]]
                print(f"    {data[0]}: {data[1]} files")
        else:
            error_info = athena.get_query_execution(QueryExecutionId=query_id)["QueryExecution"]["Status"]
            print(f"  ❌ {role_name} query failed: {status}")
            if "StateChangeReason" in error_info:
                print(f"    Reason: {error_info['StateChangeReason']}")
            
    except Exception as e:
        print(f"  ❌ {role_name} test failed: {e}")

def main():
    print("🚀 Lake Formation RBAC Test")
    print("=" * 50)
    
    # Test Core role
    core_role = "arn:aws:iam::047719628777:role/OptionAIngestionDemoPy-AnalystCoreRoleF1795BD7-UFQUIDydLNMa"
    test_role_access(core_role, "Core Role", "wg_core_read_demo")
    
    # Test PII role
    pii_role = "arn:aws:iam::047719628777:role/OptionAIngestionDemoPy-AnalystPiiRole0E9F1092-qj0y9WP3JMLG"
    test_role_access(pii_role, "PII Role", "wg_pii_read_demo")
    
    print("\n🎉 Test completed!")

if __name__ == "__main__":
    main()
