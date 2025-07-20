import * as cdk from 'aws-cdk-lib';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import { Construct } from 'constructs';

export interface DatabaseStackProps extends cdk.StackProps {
  vpc: ec2.Vpc;
}

export class DatabaseStack extends cdk.Stack {
  public readonly database: rds.DatabaseInstance;

  constructor(scope: Construct, id: string, props: DatabaseStackProps) {
    super(scope, id, props);

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
