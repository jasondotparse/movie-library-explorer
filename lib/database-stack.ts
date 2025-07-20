import * as cdk from 'aws-cdk-lib';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as customResources from 'aws-cdk-lib/custom-resources';
import * as path from 'path';
import { Construct } from 'constructs';

export interface DatabaseStackProps extends cdk.StackProps {
  vpc: ec2.Vpc;
}

export class DatabaseStack extends cdk.Stack {
  public readonly database: rds.DatabaseInstance;

  constructor(scope: Construct, id: string, props: DatabaseStackProps) {
    super(scope, id, props);

    // Create security group for Lambda to connect to RDS
    const lambdaSecurityGroup = new ec2.SecurityGroup(this, 'DbInitLambdaSecurityGroup', {
      vpc: props.vpc,
      description: 'Security group for database initialization Lambda',
      allowAllOutbound: true,
    });

    // Create RDS PostgreSQL instance
    this.database = new rds.DatabaseInstance(this, 'MovieDatabase', {
      engine: rds.DatabaseInstanceEngine.postgres({
        version: rds.PostgresEngineVersion.VER_14,
      }),
      instanceType: ec2.InstanceType.of(
        ec2.InstanceClass.T3,
        ec2.InstanceSize.SMALL
      ),
      vpc: props.vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
      databaseName: 'movieexplorer',
      allocatedStorage: 100,
      maxAllocatedStorage: 200,
      storageEncrypted: true,
      multiAz: false, // Set to false for development
      autoMinorVersionUpgrade: true,
      deleteAutomatedBackups: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY, // For development only
      deletionProtection: false, // For development only
      backupRetention: cdk.Duration.days(1),
    });

    // Allow Lambda security group to connect to RDS
    this.database.connections.allowFrom(lambdaSecurityGroup, ec2.Port.tcp(5432));

    // Create Lambda function for database initialization using Docker
    const dbInitLambda = new lambda.DockerImageFunction(this, 'DbInitFunction', {
      code: lambda.DockerImageCode.fromImageAsset(
        path.join(__dirname, '../lambda/db_init'),
        {
          platform: cdk.aws_ecr_assets.Platform.LINUX_AMD64,
        }
      ),
      architecture: lambda.Architecture.X86_64,
      vpc: props.vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
      securityGroups: [lambdaSecurityGroup],
      timeout: cdk.Duration.minutes(5),
      memorySize: 256,
      environment: {
        'LOG_LEVEL': 'INFO',
      },
    });

    // Grant Lambda permission to read the database secret
    if (this.database.secret) {
      this.database.secret.grantRead(dbInitLambda);
    }

    // Grant Lambda additional permissions for Secrets Manager
    dbInitLambda.addToRolePolicy(new iam.PolicyStatement({
      actions: [
        'secretsmanager:GetSecretValue',
        'secretsmanager:DescribeSecret',
      ],
      resources: [this.database.secret?.secretArn || '*'],
    }));

    // Create custom resource provider
    const provider = new customResources.Provider(this, 'DbInitProvider', {
      onEventHandler: dbInitLambda,
      logRetention: cdk.aws_logs.RetentionDays.ONE_WEEK,
    });

    // Create custom resource to trigger database initialization
    const dbInitResource = new cdk.CustomResource(this, 'DbInitResource', {
      serviceToken: provider.serviceToken,
      properties: {
        DatabaseSecretArn: this.database.secret?.secretArn,
        // Force update on every deployment
        ForceUpdate: Date.now().toString(),
      },
    });

    // Ensure the custom resource waits for the database to be created
    dbInitResource.node.addDependency(this.database);

    // Output database endpoint
    new cdk.CfnOutput(this, 'DatabaseEndpoint', {
      value: this.database.dbInstanceEndpointAddress,
      description: 'RDS Database Endpoint',
      exportName: 'MovieExplorerDatabaseEndpoint',
    });

    // Output database secret ARN
    new cdk.CfnOutput(this, 'DatabaseSecretArn', {
      value: this.database.secret?.secretArn || 'No secret created',
      description: 'Database Secret ARN',
      exportName: 'MovieExplorerDatabaseSecretArn',
    });
  }
}
