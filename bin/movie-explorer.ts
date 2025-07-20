#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import { Construct } from 'constructs';
import { DatabaseStack } from '../lib/database-stack';
import { AuthStack } from '../lib/auth-stack';
import { FrontendStack } from '../lib/frontend-stack';
import { ApiStack } from '../lib/api-stack';
import { EtlStack } from '../lib/etl-stack';

const app = new cdk.App();

// Environment configuration
const ACCOUNT = '756021455455';
const REGION = 'us-west-1';

const env = { account: ACCOUNT, region: REGION };

// Create a VPC stack to be shared across all resources
class VpcStack extends cdk.Stack {
  public readonly vpc: ec2.Vpc;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    this.vpc = new ec2.Vpc(this, 'MovieExplorerVpc', {
      maxAzs: 2,
      natGateways: 1,
      subnetConfiguration: [
        {
          name: 'Public',
          subnetType: ec2.SubnetType.PUBLIC,
          cidrMask: 24,
        },
        {
          name: 'Private',
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
          cidrMask: 24,
        }
      ],
    });
  }
}

// Create VPC stack first
const vpcStack = new VpcStack(app, 'MovieExplorerVpc', {
  env,
  description: 'Movie Explorer VPC Stack - Shared networking resources',
});

// Deploy stacks with dependencies
const databaseStack = new DatabaseStack(app, 'MovieExplorerDatabase', {
  env,
  description: 'Movie Explorer Database Stack - RDS PostgreSQL',
  vpc: vpcStack.vpc,
});

const authStack = new AuthStack(app, 'MovieExplorerAuth', {
  env,
  description: 'Movie Explorer Authentication Stack - Cognito',
});

const apiStack = new ApiStack(app, 'MovieExplorerApi', {
  env,
  description: 'Movie Explorer API Stack - API Gateway and Lambda',
  vpc: vpcStack.vpc,
  database: databaseStack.database,
  userPool: authStack.userPool,
});

const frontendStack = new FrontendStack(app, 'MovieExplorerFrontend', {
  env,
  description: 'Movie Explorer Frontend Stack - S3 and CloudFront',
  api: apiStack.api,
  userPool: authStack.userPool,
  userPoolClient: authStack.userPoolClient,
});

const etlStack = new EtlStack(app, 'MovieExplorerEtl', {
  env,
  description: 'Movie Explorer ETL Stack - ECS Fargate',
  vpc: vpcStack.vpc,
  database: databaseStack.database,
});

// Add dependencies
databaseStack.addDependency(vpcStack);
apiStack.addDependency(vpcStack);
apiStack.addDependency(databaseStack);
apiStack.addDependency(authStack);
frontendStack.addDependency(apiStack);
etlStack.addDependency(vpcStack);
etlStack.addDependency(databaseStack);
