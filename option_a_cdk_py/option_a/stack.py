"""
AWS Option A Demo Stack - EventBridge → SQS → Lambda → S3 Data Lake

This stack creates a complete data lake infrastructure with:
- EventBridge cron triggers → Planner Lambda → SQS queues → Worker Lambda → S3
- Glue Database + Crawler for data catalog
- Athena WorkGroup for querying
- CloudWatch monitoring and alarms
- Lake Formation RBAC (requires manual setup - see LAKE_FORMATION_SETUP.md)

Lake Formation RBAC is temporarily disabled due to CloudFormation execution role limitations.
Follow the guide in LAKE_FORMATION_SETUP.md to enable it.
"""

from typing import Dict
import json

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    Duration,
    aws_s3 as s3,
    aws_kms as kms,
    aws_lambda as _lambda,
    aws_sqs as sqs,
    aws_lambda_event_sources as lambda_events,
    aws_iam as iam,
    aws_events as events,
    aws_events_targets as targets,
    aws_logs as logs,
    aws_glue as glue,
    aws_athena as athena,
    aws_cloudwatch as cw,
    aws_lakeformation as lf,
)

class OptionAStack(Stack):
    def __init__(self, scope: cdk.App, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # KMS and Buckets
        kms_key = kms.Key(self, "DataLakeKey", enable_key_rotation=True)

        data_lake = s3.Bucket(
            self, "DataLakeBucket",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=kms_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            versioned=True,
        )

        athena_results = s3.Bucket(
            self, "AthenaResultsBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            lifecycle_rules=[s3.LifecycleRule(expiration=Duration.days(30))],
        )

        # SQS Queues + DLQs
        endpoints = ["api-a", "api-b", "api-c", "api-d"]
        queues: Dict[str, sqs.Queue] = {}
        dlqs: Dict[str, sqs.Queue] = {}

        for ep in endpoints:
            dlq = sqs.Queue(
                self, f"{ep.upper()}DLQ",
                retention_period=Duration.days(14),
                encryption=sqs.QueueEncryption.SQS_MANAGED,
            )
            q = sqs.Queue(
                self, f"{ep.upper()}Queue",
                visibility_timeout=Duration.seconds(180),
                retention_period=Duration.days(4),
                dead_letter_queue=sqs.DeadLetterQueue(queue=dlq, max_receive_count=5),
                encryption=sqs.QueueEncryption.SQS_MANAGED,
            )
            dlqs[ep] = dlq
            queues[ep] = q

        # Planner Lambda
        planner_fn = _lambda.Function(
            self, "PlannerFn",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="planner.handler",
            code=_lambda.Code.from_asset("lambda"),
            timeout=Duration.seconds(60),
            memory_size=256,
            log_retention=logs.RetentionDays.ONE_WEEK,
            environment={
                "QUEUE_URLS_JSON": json.dumps({ep: queues[ep].queue_url for ep in endpoints}),
            },
        )
        for q in queues.values():
            q.grant_send_messages(planner_fn)

        # EventBridge cron
        rule = events.Rule(
            self, "CronRule",
            schedule=events.Schedule.cron(minute="*/5"),
        )
        rule.add_target(targets.LambdaFunction(planner_fn))

        # Worker Lambda
        worker_fn = _lambda.Function(
            self, "WorkerFn",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="worker.handler",
            code=_lambda.Code.from_asset("lambda"),
            timeout=Duration.seconds(180),
            memory_size=512,
            log_retention=logs.RetentionDays.ONE_WEEK,
            environment={
                "DATA_LAKE_BUCKET": data_lake.bucket_name,
                "USE_REAL_HTTP": "false",
                "MAX_RETRIES": "5",
                "QPS_SLEEP_MS": "50",
                "ENDPOINT_MAP": json.dumps({
                    "api-a": "https://example.com/api-a",
                    "api-b": "https://example.com/api-b",
                    "api-c": "https://example.com/api-c",
                    "api-d": "https://example.com/api-d",
                }),
            },
        )
        data_lake.grant_read(worker_fn)
        data_lake.grant_put(worker_fn)

        # SQS event sources → Worker
        for ep, q in queues.items():
            worker_fn.add_event_source(lambda_events.SqsEventSource(
                q, batch_size=2, max_batching_window=Duration.seconds(2)
            ))
            q.grant_consume_messages(worker_fn)

        # Glue Database & Crawler
        db = glue.CfnDatabase(self, "DataLakeDb", catalog_id=self.account, database_input=glue.CfnDatabase.DatabaseInputProperty(name="option_a_demo_db"))

        crawler_role = iam.Role(self, "CrawlerRole", assumed_by=iam.ServicePrincipal("glue.amazonaws.com"))
        data_lake.grant_read(crawler_role)
        
        # Add CloudWatch Logs permissions for crawler
        crawler_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:DescribeLogGroups",
                "logs:DescribeLogStreams"
            ],
            resources=["arn:aws:logs:*:*:*"]
        ))
        
        # Add Glue Data Catalog permissions for crawler
        crawler_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "glue:GetDatabase",
                "glue:GetDatabases",
                "glue:CreateTable",
                "glue:UpdateTable",
                "glue:GetTable",
                "glue:GetTables",
                "glue:DeleteTable",
                "glue:BatchCreatePartition",
                "glue:BatchDeletePartition",
                "glue:GetPartition",
                "glue:GetPartitions",
                "glue:BatchGetPartition",
                "glue:CreatePartition",
                "glue:UpdatePartition",
                "glue:DeletePartition"
            ],
            resources=["*"]
        ))

        # Use L1 for crawler for full control
        crawler = glue.CfnCrawler(
            self, "RawCrawler",
            role=crawler_role.role_arn,
            database_name="option_a_demo_db",
            name="option-a-raw-crawler",
            targets=glue.CfnCrawler.TargetsProperty(
                s3_targets=[glue.CfnCrawler.S3TargetProperty(path=f"s3://{data_lake.bucket_name}/raw/")]
            ),
            schedule=glue.CfnCrawler.ScheduleProperty(schedule_expression="cron(*/10 * * * ? *)"),
            schema_change_policy=glue.CfnCrawler.SchemaChangePolicyProperty(
                update_behavior="UPDATE_IN_DATABASE",
                delete_behavior="DEPRECATE_IN_DATABASE",
            ),
        )

        # Athena WorkGroup
        wg_default = athena.CfnWorkGroup(
            self, "AthenaWG",
            name="option_a_demo_wg",
            work_group_configuration=athena.CfnWorkGroup.WorkGroupConfigurationProperty(
                result_configuration=athena.CfnWorkGroup.ResultConfigurationProperty(
                    output_location=f"s3://{athena_results.bucket_name}/"
                ),
                publish_cloud_watch_metrics_enabled=True,
                enforce_work_group_configuration=True,
            ),
            state="ENABLED",
        )

        # ========== Lake Formation RBAC scaffolding (temporarily disabled) ==========
        # 
        # MANUAL SETUP REQUIRED BEFORE ENABLING:
        # 1. Deploy with only LF admin role first (CFN exec role removed from admins)
        # 2. After successful deployment, manually add CFN exec role to LF admins:
        #    - Go to AWS Console → Lake Formation → Settings
        #    - Add: arn:aws:iam::{account}:role/cdk-hnb659fds-cfn-exec-role-{account}-{region}
        # 3. Add Lake Formation permissions to CFN exec role in IAM Console
        # 4. Run: cdk deploy --all --require-approval never
        #
        # See LAKE_FORMATION_SETUP.md for detailed step-by-step instructions
        """
        # Lake Formation Admin Role - has full permissions to manage LF settings
        lf_admin_role = iam.Role(self, "LFAdminRole", assumed_by=iam.AccountRootPrincipal())
        
        # Demo Analyst Roles - different permission levels for RBAC demonstration
        analyst_core_role = iam.Role(self, "AnalystCoreRole",
                                     assumed_by=iam.AccountRootPrincipal(),
                                     description="Demo analyst role (no PII, limited rows)")
        analyst_pii_role = iam.Role(self, "AnalystPiiRole",
                                    assumed_by=iam.AccountRootPrincipal(),
                                    description="Demo analyst role with PII access")

        # Grant Athena and Glue permissions to analyst roles
        # Note: Lake Formation will gate actual data access based on LF permissions
        for r in [analyst_core_role, analyst_pii_role]:
            r.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonAthenaFullAccess'))
            r.add_to_policy(iam.PolicyStatement(
                actions=[
                    "glue:GetDatabase","glue:GetDatabases","glue:GetTable","glue:GetTables",
                    "glue:GetPartition","glue:GetPartitions",
                    "lakeformation:GetDataAccess","lakeformation:SearchTablesByLFTags","lakeformation:GetResourceLFTags"
                ],
                resources=["*"]
            ))

        # Register S3 bucket as Lake Formation data location
        # This allows Lake Formation to manage permissions on the S3 data
        lf_location = lf.CfnResource(self, "LFDataLocation", resource_arn=data_lake.bucket_arn, use_service_linked_role=True)

        # Configure Lake Formation administrators
        # IMPORTANT: Only use the admin role initially - CFN execution role needs manual setup
        lf_admins = [
            lf.CfnDataLakeSettings.DataLakePrincipalProperty(
                data_lake_principal_identifier=lf_admin_role.role_arn
            )
        ]
        lf.CfnDataLakeSettings(
            self, "DataLakeSettings",
            admins=lf_admins
        )

        # Grant DATA_LOCATION_ACCESS permission to analyst roles
        # This allows them to access data in the registered S3 location
        for r in [analyst_core_role, analyst_pii_role]:
            lf.CfnPrincipalPermissions(
                self, f"DataLocAccess{r.node.id}",
                permissions=["DATA_LOCATION_ACCESS"],
                permissions_with_grant_option=[],
                principal=lf.CfnPrincipalPermissions.DataLakePrincipalProperty(
                    data_lake_principal_identifier=r.role_arn
                ),
                resource=lf.CfnPrincipalPermissions.ResourceProperty(
                    data_location=lf.CfnPrincipalPermissions.DataLocationResourceProperty(
                        catalog_id=self.account,
                        resource_arn=data_lake.bucket_arn
                    )
                )
            )

        # Grant DESCRIBE permission on the Glue database
        # This allows analyst roles to see database metadata
        for r in [analyst_core_role, analyst_pii_role]:
            lf.CfnPrincipalPermissions(
                self, f"DbDescribe{r.node.id}",
                permissions=["DESCRIBE"],
                permissions_with_grant_option=[],
                principal=lf.CfnPrincipalPermissions.DataLakePrincipalProperty(
                    data_lake_principal_identifier=r.role_arn
                ),
                resource=lf.CfnPrincipalPermissions.ResourceProperty(
                    database=lf.CfnPrincipalPermissions.DatabaseResourceProperty(
                        name="option_a_demo_db",
                        catalog_id=self.account
                    )
                )
            )

        # Create separate Athena workgroups for each analyst role
        # This segregates query results and allows different configurations
        core_wg = athena.CfnWorkGroup(
            self, "AthenaCoreWG",
            name="wg_core_read_demo",
            work_group_configuration=athena.CfnWorkGroup.WorkGroupConfigurationProperty(
                result_configuration=athena.CfnWorkGroup.ResultConfigurationProperty(
                    output_location=f"s3://{athena_results.bucket_name}/core/"
                ),
                publish_cloud_watch_metrics_enabled=True,
                enforce_work_group_configuration=True,
            ),
        )
        pii_wg = athena.CfnWorkGroup(
            self, "AthenaPiiWG",
            name="wg_pii_read_demo",
            work_group_configuration=athena.CfnWorkGroup.WorkGroupConfigurationProperty(
                result_configuration=athena.CfnWorkGroup.ResultConfigurationProperty(
                    output_location=f"s3://{athena_results.bucket_name}/pii/"
                ),
                publish_cloud_watch_metrics_enabled=True,
                enforce_work_group_configuration=True,
            ),
        )
        """

        # ========== CloudWatch Alarms (unchanged) ==========
        # CloudWatch Alarms
        for ep, dlq in dlqs.items():
            cw.Alarm(
                self, f"{ep.upper()}DLQAlarm",
                metric=dlq.metric_approximate_number_of_messages_visible(),
                threshold=0,
                comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
                evaluation_periods=1,
                datapoints_to_alarm=1,
            )

        for ep, q in queues.items():
            cw.Alarm(
                self, f"{ep.upper()}AgeAlarm",
                metric=q.metric_approximate_age_of_oldest_message(),
                threshold=300,
                comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
                evaluation_periods=1,
                datapoints_to_alarm=1,
            )

        cw.Alarm(
            self, "WorkerErrorsAlarm",
            metric=worker_fn.metric_errors(period=cdk.Duration.minutes(5)),
            threshold=1,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            evaluation_periods=1,
            datapoints_to_alarm=1,
        )

        # Outputs
        cdk.CfnOutput(self, "DataLakeBucketName", value=data_lake.bucket_name)
        cdk.CfnOutput(self, "AthenaResultsBucketName", value=athena_results.bucket_name)
        cdk.CfnOutput(self, "DataLakeKeyArn", value=kms_key.key_arn)
        cdk.CfnOutput(self, "GlueDatabaseName", value="option_a_demo_db")
        cdk.CfnOutput(self, "GlueCrawlerName", value=crawler.name or "option-a-raw-crawler")
        cdk.CfnOutput(self, "WorkGroupName", value=wg_default.name or "option_a_demo_wg")
        cdk.CfnOutput(self, "PlannerFunctionName", value=planner_fn.function_name)
        cdk.CfnOutput(self, "WorkerFunctionName", value=worker_fn.function_name)
        
        # Lake Formation RBAC outputs (uncomment when LF RBAC is enabled)
        # cdk.CfnOutput(self, "AnalystCoreRoleArn", value=analyst_core_role.role_arn)
        # cdk.CfnOutput(self, "AnalystPiiRoleArn", value=analyst_pii_role.role_arn)
        # cdk.CfnOutput(self, "LFAdminRoleArn", value=lf_admin_role.role_arn)
        # cdk.CfnOutput(self, "AthenaCoreWGOutput", value=core_wg.name or "wg_core_read_demo")
        # cdk.CfnOutput(self, "AthenaPiiWGOutput", value=pii_wg.name or "wg_pii_read_demo")
