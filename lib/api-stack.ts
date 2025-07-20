import * as cdk from 'aws-cdk-lib';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import { Construct } from 'constructs';

export interface ApiStackProps extends cdk.StackProps {
  vpc: ec2.Vpc;
  database: rds.DatabaseInstance;
  userPool: cognito.UserPool;
}

export class ApiStack extends cdk.Stack {
  public readonly api: apigateway.RestApi;

  constructor(scope: Construct, id: string, props: ApiStackProps) {
    super(scope, id, props);

    // Create IAM role for API Gateway to write logs to CloudWatch
    const apiGatewayLogsRole = new iam.Role(this, 'ApiGatewayCloudWatchLogsRole', {
      assumedBy: new iam.ServicePrincipal('apigateway.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AmazonAPIGatewayPushToCloudWatchLogs')
      ],
    });

    // Set the CloudWatch role for API Gateway
    const cfnAccount = new apigateway.CfnAccount(this, 'ApiGatewayAccount', {
      cloudWatchRoleArn: apiGatewayLogsRole.roleArn,
    });

    // Create REST API
    this.api = new apigateway.RestApi(this, 'MovieExplorerApi', {
      restApiName: 'movie-explorer-api',
      description: 'Movie Explorer API Gateway',
      deployOptions: {
        stageName: 'v1',
        tracingEnabled: true,
        dataTraceEnabled: false,
        loggingLevel: apigateway.MethodLoggingLevel.INFO,
        metricsEnabled: true,
      },
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: ['Content-Type', 'X-Amz-Date', 'Authorization', 'X-Api-Key', 'X-Amz-Security-Token'],
      },
    });

    // Create Cognito authorizer for web UI users
    const cognitoAuthorizer = new apigateway.CognitoUserPoolsAuthorizer(this, 'CognitoAuthorizer', {
      cognitoUserPools: [props.userPool],
      authorizerName: 'MovieExplorerCognitoAuth',
    });

    // Placeholder Lambda function (to be implemented later)
    const getMoviesLambda = new lambda.Function(this, 'GetMoviesFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'index.handler',
      code: lambda.Code.fromInline(`
def handler(event, context):
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': '{"message": "Movies endpoint - to be implemented"}'
    }
      `),
      vpc: props.vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
      environment: {
        DATABASE_ENDPOINT: props.database.dbInstanceEndpointAddress,
        DATABASE_NAME: 'movieexplorer',
      },
    });

    // Grant database access to Lambda
    props.database.grantConnect(getMoviesLambda);

    // Create movies resource
    const movies = this.api.root.addResource('movies');
    
    // Add GET method with BOTH Cognito and IAM auth support
    movies.addMethod('GET', new apigateway.LambdaIntegration(getMoviesLambda), {
      authorizationType: apigateway.AuthorizationType.COGNITO,
      authorizer: cognitoAuthorizer,
    });

    // Also add IAM auth support by updating the method's properties
    // This allows both Cognito tokens and AWS IAM signatures
    const cfnMethod = movies.node.findChild('GET') as apigateway.CfnMethod;
    cfnMethod.authorizationType = 'AWS_IAM';
    cfnMethod.authorizerId = undefined;

    // Outputs
    new cdk.CfnOutput(this, 'ApiEndpoint', {
      value: this.api.url,
      description: 'API Gateway endpoint URL',
      exportName: 'MovieExplorerApiEndpoint',
    });
  }
}
