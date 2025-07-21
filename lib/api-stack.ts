import * as cdk from 'aws-cdk-lib';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as lambdaEventSources from 'aws-cdk-lib/aws-lambda-event-sources';
import * as path from 'path';
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
        cacheClusterEnabled: true,
        cacheClusterSize: '0.5',
        // Configure method-level caching for GET endpoints with 30s TTL for data freshness
        methodOptions: {
          '/api/dashboard/GET': {
            cachingEnabled: true,
            cacheTtl: cdk.Duration.seconds(30),
            metricsEnabled: true,
          },
          '/api/movies/search/GET': {
            cachingEnabled: true,
            cacheTtl: cdk.Duration.seconds(30),
            metricsEnabled: true,
          },
          '/api/movies/filter/GET': {
            cachingEnabled: true,
            cacheTtl: cdk.Duration.seconds(30),
            metricsEnabled: true,
          },
          '/api/movies/top-rated/GET': {
            cachingEnabled: true,
            cacheTtl: cdk.Duration.seconds(30),
            metricsEnabled: true,
          },
        },
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

    // Create security group for Lambda to connect to RDS
    const lambdaSecurityGroup = new ec2.SecurityGroup(this, 'ApiLambdaSecurityGroup', {
      vpc: props.vpc,
      description: 'Security group for API Lambda functions',
      allowAllOutbound: true,
    });

    // Note: We cannot directly modify the database security group here due to circular dependency
    // The security group rule must be added manually or through a separate process
    
    // Create GET handler Lambda function using Docker
    const getMoviesLambda = new lambda.DockerImageFunction(this, 'GetMoviesFunction', {
      code: lambda.DockerImageCode.fromImageAsset(
        path.join(__dirname, '../lambda/get_handler'),
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
      timeout: cdk.Duration.seconds(30),
      memorySize: 512,
      environment: {
        DATABASE_ENDPOINT: props.database.dbInstanceEndpointAddress,
        DATABASE_NAME: 'movieexplorer',
        DATABASE_SECRET_ARN: props.database.secret?.secretArn || '',
        LOG_LEVEL: 'INFO',
      },
    });

    // Grant Lambda permission to read the database secret
    if (props.database.secret) {
      props.database.secret.grantRead(getMoviesLambda);
    }

    // Grant Lambda additional permissions for Secrets Manager
    getMoviesLambda.addToRolePolicy(new iam.PolicyStatement({
      actions: [
        'secretsmanager:GetSecretValue',
        'secretsmanager:DescribeSecret',
      ],
      resources: [props.database.secret?.secretArn || '*'],
    }));

    // Create API resources
    const api = this.api.root.addResource('api');
    const movies = api.addResource('movies');
    const dashboard = api.addResource('dashboard');
    
    // Add search endpoint
    const search = movies.addResource('search');
    search.addMethod('GET', new apigateway.LambdaIntegration(getMoviesLambda), {
      authorizationType: apigateway.AuthorizationType.COGNITO,
      authorizer: cognitoAuthorizer,
    });
    
    // Add filter endpoint
    const filter = movies.addResource('filter');
    filter.addMethod('GET', new apigateway.LambdaIntegration(getMoviesLambda), {
      authorizationType: apigateway.AuthorizationType.COGNITO,
      authorizer: cognitoAuthorizer,
    });
    
    // Add top-rated endpoint
    const topRated = movies.addResource('top-rated');
    topRated.addMethod('GET', new apigateway.LambdaIntegration(getMoviesLambda), {
      authorizationType: apigateway.AuthorizationType.COGNITO,
      authorizer: cognitoAuthorizer,
    });
    
    // Add dashboard endpoint
    dashboard.addMethod('GET', new apigateway.LambdaIntegration(getMoviesLambda), {
      authorizationType: apigateway.AuthorizationType.COGNITO,
      authorizer: cognitoAuthorizer,
    });

    // Create SQS queue for movie creation
    const movieQueue = new sqs.Queue(this, 'MovieCreationQueue', {
      queueName: 'movie-explorer-creation-queue',
      visibilityTimeout: cdk.Duration.seconds(60),
      retentionPeriod: cdk.Duration.days(4),
    });

    // Create IAM role for API Gateway to send messages to SQS
    const apiGatewayToSqsRole = new iam.Role(this, 'ApiGatewayToSqsRole', {
      assumedBy: new iam.ServicePrincipal('apigateway.amazonaws.com'),
      inlinePolicies: {
        SendMessagePolicy: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              actions: ['sqs:SendMessage'],
              resources: [movieQueue.queueArn],
            }),
          ],
        }),
      },
    });

    // Create request validator for POST /api/movies
    const requestValidator = new apigateway.RequestValidator(this, 'MoviePostValidator', {
      restApi: this.api,
      requestValidatorName: 'movie-post-validator',
      validateRequestBody: true,
      validateRequestParameters: false,
    });

    // Create request model for movie data
    const movieModel = new apigateway.Model(this, 'MovieModel', {
      restApi: this.api,
      contentType: 'application/json',
      modelName: 'MovieInput',
      schema: {
        type: apigateway.JsonSchemaType.OBJECT,
        properties: {
          title: {
            type: apigateway.JsonSchemaType.STRING,
            minLength: 1,
            maxLength: 255,
          },
          genre: {
            type: apigateway.JsonSchemaType.STRING,
            minLength: 1,
            maxLength: 100,
          },
          rating: {
            type: apigateway.JsonSchemaType.NUMBER,
            minimum: 0,
            maximum: 10,
          },
          year: {
            type: apigateway.JsonSchemaType.INTEGER,
            minimum: 1900,
            maximum: 2100,
          },
        },
        required: ['title', 'genre', 'rating', 'year'],
      },
    });

    // Create POST method with direct SQS integration
    movies.addMethod('POST', new apigateway.AwsIntegration({
      service: 'sqs',
      path: `${cdk.Aws.ACCOUNT_ID}/${movieQueue.queueName}`,
      integrationHttpMethod: 'POST',
      options: {
        credentialsRole: apiGatewayToSqsRole,
        requestParameters: {
          'integration.request.header.Content-Type': "'application/x-www-form-urlencoded'",
        },
        requestTemplates: {
          'application/json': `Action=SendMessage&MessageBody={
            "id": "$context.requestId",
            "title": $input.json('$.title'),
            "genre": $input.json('$.genre'),
            "rating": $input.json('$.rating'),
            "year": $input.json('$.year'),
            "created_at": "$context.requestTime"
          }`,
        },
        integrationResponses: [
          {
            statusCode: '201',
            responseTemplates: {
              'application/json': JSON.stringify({
                id: '$context.requestId',
                message: 'Movie creation request received',
              }),
            },
            responseParameters: {
              'method.response.header.Access-Control-Allow-Origin': "'*'",
            },
          },
          {
            statusCode: '400',
            selectionPattern: '4\\d{2}',
            responseTemplates: {
              'application/json': JSON.stringify({
                error: {
                  code: 'BAD_REQUEST',
                  message: 'Invalid request',
                },
              }),
            },
            responseParameters: {
              'method.response.header.Access-Control-Allow-Origin': "'*'",
            },
          },
        ],
      },
    }), {
      authorizationType: apigateway.AuthorizationType.COGNITO,
      authorizer: cognitoAuthorizer,
      requestValidator: requestValidator,
      requestModels: {
        'application/json': movieModel,
      },
      methodResponses: [
        {
          statusCode: '201',
          responseParameters: {
            'method.response.header.Access-Control-Allow-Origin': true,
          },
        },
        {
          statusCode: '400',
          responseParameters: {
            'method.response.header.Access-Control-Allow-Origin': true,
          },
        },
      ],
    });

    // Create async processor Lambda function
    const asyncProcessorLambda = new lambda.DockerImageFunction(this, 'AsyncProcessorFunction', {
      code: lambda.DockerImageCode.fromImageAsset(
        path.join(__dirname, '../lambda/async_processor'),
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
      timeout: cdk.Duration.seconds(60),
      memorySize: 256,
      environment: {
        DATABASE_ENDPOINT: props.database.dbInstanceEndpointAddress,
        DATABASE_NAME: 'movieexplorer',
        DATABASE_SECRET_ARN: props.database.secret?.secretArn || '',
        LOG_LEVEL: 'INFO',
      },
    });

    // Grant Lambda permission to read the database secret
    if (props.database.secret) {
      props.database.secret.grantRead(asyncProcessorLambda);
    }

    // Grant Lambda additional permissions for Secrets Manager
    asyncProcessorLambda.addToRolePolicy(new iam.PolicyStatement({
      actions: [
        'secretsmanager:GetSecretValue',
        'secretsmanager:DescribeSecret',
      ],
      resources: [props.database.secret?.secretArn || '*'],
    }));

    // Configure Lambda to be triggered by SQS
    asyncProcessorLambda.addEventSource(new lambdaEventSources.SqsEventSource(movieQueue, {
      batchSize: 10,
      maxBatchingWindow: cdk.Duration.seconds(5),
    }));

    // Outputs
    new cdk.CfnOutput(this, 'ApiEndpoint', {
      value: this.api.url,
      description: 'API Gateway endpoint URL',
      exportName: 'MovieExplorerApiEndpoint',
    });

    new cdk.CfnOutput(this, 'SqsQueueUrl', {
      value: movieQueue.queueUrl,
      description: 'SQS Queue URL for movie creation',
    });
  }
}
