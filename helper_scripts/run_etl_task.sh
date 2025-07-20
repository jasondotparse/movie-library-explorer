#!/bin/bash

# Run the ETL task using AWS CLI
# This script triggers a one-time execution of the ETL task in ECS

CLUSTER="movie-explorer-etl"
TASK_DEFINITION="MovieExplorerEtlEtlTaskDefinitionBC054B6E"
REGION="us-west-1"

# Get VPC and subnet IDs
VPC_ID=$(aws ec2 describe-vpcs --region $REGION --filters "Name=tag:aws:cloudformation:stack-name,Values=MovieExplorerVpc" --query 'Vpcs[0].VpcId' --output text)
# Use public subnets to ensure internet access for ECR and Google Drive API
SUBNET_IDS=$(aws ec2 describe-subnets --region $REGION --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Name,Values=*Public*" --query 'Subnets[*].SubnetId' --output text | tr '\t' ',')

echo "Running ETL task..."
echo "Cluster: $CLUSTER"
echo "Task Definition: $TASK_DEFINITION"
echo "Subnets: $SUBNET_IDS"

# Get the ETL security group
SECURITY_GROUP=$(aws cloudformation list-exports --region $REGION --query "Exports[?Name=='MovieExplorerEtlTaskSecurityGroupId'].Value" --output text)

if [ -z "$SECURITY_GROUP" ]; then
  echo "Warning: Could not find ETL security group, using default"
  SECURITY_GROUP_PARAM=""
else
  echo "Security Group: $SECURITY_GROUP"
  SECURITY_GROUP_PARAM=",securityGroups=[$SECURITY_GROUP]"
fi

# Run the task
TASK_ARN=$(aws ecs run-task \
  --cluster $CLUSTER \
  --task-definition $TASK_DEFINITION \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_IDS],assignPublicIp=ENABLED$SECURITY_GROUP_PARAM}" \
  --region $REGION \
  --query 'tasks[0].taskArn' \
  --output text)

if [ -z "$TASK_ARN" ]; then
  echo "Failed to start task"
  exit 1
fi

echo "Task started: $TASK_ARN"
echo ""
echo "To monitor the task, run:"
echo "aws ecs describe-tasks --cluster $CLUSTER --tasks $TASK_ARN --region $REGION"
echo ""
echo "To view logs, check CloudWatch Logs in the AWS Console or use:"
echo "aws logs tail /ecs/MovieExplorerEtlEtlTaskDefinition --follow --region $REGION"
