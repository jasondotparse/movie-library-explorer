import * as cdk from 'aws-cdk-lib';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';

export interface EtlStackProps extends cdk.StackProps {
  vpc: ec2.Vpc;
  database: rds.DatabaseInstance;
}

export class EtlStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: EtlStackProps) {
    super(scope, id, props);

    // Create ECS cluster
    const cluster = new ecs.Cluster(this, 'EtlCluster', {
      vpc: props.vpc,
      clusterName: 'movie-explorer-etl',
    });

    // Create task definition
    const taskDefinition = new ecs.FargateTaskDefinition(this, 'EtlTaskDefinition', {
      memoryLimitMiB: 2048,
      cpu: 1024,
    });

    // Add container (placeholder for now)
    const container = taskDefinition.addContainer('EtlContainer', {
      image: ecs.ContainerImage.fromRegistry('alpine:latest'), // Placeholder image
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'movie-etl',
        logRetention: logs.RetentionDays.ONE_WEEK,
      }),
      environment: {
        DATABASE_ENDPOINT: props.database.dbInstanceEndpointAddress,
        DATABASE_NAME: 'movieexplorer',
      },
    });

    // Grant database access to task
    props.database.grantConnect(taskDefinition.taskRole);

    // Grant Google Drive API access permissions
    taskDefinition.addToTaskRolePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          'secretsmanager:GetSecretValue',
        ],
        resources: ['*'], // Will be scoped to specific secret later
      })
    );

    // Create Fargate service (commented out for now as we don't have the actual ETL code)
    // const service = new ecs.FargateService(this, 'EtlService', {
    //   cluster,
    //   taskDefinition,
    //   desiredCount: 0, // Start with 0, manually trigger when needed
    //   vpcSubnets: {
    //     subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
    //   },
    // });

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
  }
}
