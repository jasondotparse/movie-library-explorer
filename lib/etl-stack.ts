import * as cdk from 'aws-cdk-lib';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Platform } from 'aws-cdk-lib/aws-ecr-assets';
import { Construct } from 'constructs';

export interface EtlStackProps extends cdk.StackProps {
  vpc: ec2.Vpc;
  database: rds.DatabaseInstance;
}

export class EtlStack extends cdk.Stack {
  public readonly gcpAccessTokenSecret: secretsmanager.Secret;

  constructor(scope: Construct, id: string, props: EtlStackProps) {
    super(scope, id, props);

    // Create Secret for GCP access token
    this.gcpAccessTokenSecret = new secretsmanager.Secret(this, 'GCPAccessTokenSecret', {
      secretName: 'GCP_access_token',
      description: 'Google Cloud Platform OAuth2 token for accessing Google Drive API',
      secretStringValue: cdk.SecretValue.unsafePlainText('{}'), // Empty string as default
    });

    // Create ECS cluster
    const cluster = new ecs.Cluster(this, 'EtlCluster', {
      vpc: props.vpc,
      clusterName: 'movie-explorer-etl',
    });

    // Create security group for ECS tasks with proper egress rules
    const taskSecurityGroup = new ec2.SecurityGroup(this, 'EtlTaskSecurityGroup', {
      vpc: props.vpc,
      description: 'Security group for ETL tasks',
      allowAllOutbound: true, // This ensures all outbound traffic is allowed
    });

    // Create task definition
    const taskDefinition = new ecs.FargateTaskDefinition(this, 'EtlTaskDefinition', {
      memoryLimitMiB: 2048,
      cpu: 1024,
    });

    taskDefinition.executionRole?.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonECSTaskExecutionRolePolicy')
    );

    // Add container with our ETL worker
    const container = taskDefinition.addContainer('EtlContainer', {
      image: ecs.ContainerImage.fromAsset('./etl_worker', {
        platform: Platform.LINUX_AMD64, // Ensure we build for x86_64 platform
      }),
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'movie-etl',
        logRetention: logs.RetentionDays.ONE_WEEK,
      }),
      environment: {
        DATABASE_ENDPOINT: props.database.dbInstanceEndpointAddress,
        DATABASE_NAME: 'movieexplorer',
        GCP_SECRET_NAME: this.gcpAccessTokenSecret.secretName,
        TARGET_FOLDER_ID: '1Z-Bqt69UgrGkwo0ArjHaNrA7uUmUm2r6',
        AWS_REGION: this.region,
      },
    });

    // Grant database access to task
    props.database.grantConnect(taskDefinition.taskRole);

    // Grant access to the GCP token secret
    this.gcpAccessTokenSecret.grantRead(taskDefinition.taskRole);

    // Outputs
    new cdk.CfnOutput(this, 'ClusterArn', {
      value: cluster.clusterArn,
      description: 'ECS Cluster ARN',
      exportName: 'MovieExplorerEtlClusterArn',
    });

    new cdk.CfnOutput(this, 'TaskDefinitionArn', {
      value: taskDefinition.taskDefinitionArn,
      description: 'ETL Task Definition ARN',
      exportName: 'MovieExplorerEtlTaskDefinitionArn',
    });

    new cdk.CfnOutput(this, 'GCPTokenSecretArn', {
      value: this.gcpAccessTokenSecret.secretArn,
      description: 'GCP Access Token Secret ARN',
      exportName: 'MovieExplorerGCPTokenSecretArn',
    });

    new cdk.CfnOutput(this, 'TaskSecurityGroupId', {
      value: taskSecurityGroup.securityGroupId,
      description: 'Security Group ID for ETL tasks',
      exportName: 'MovieExplorerEtlTaskSecurityGroupId',
    });

    // Note: When running tasks, use public subnets with assignPublicIp=ENABLED
    // since there's no NAT Gateway configured in the VPC
    new cdk.CfnOutput(this, 'NetworkingNote', {
      value: 'Run tasks in public subnets with assignPublicIp=ENABLED',
      description: 'Important networking configuration for running tasks',
    });
  }
}
