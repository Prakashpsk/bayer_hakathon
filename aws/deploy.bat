@echo off
REM ============================================================
REM  Deploy Incident Commander to AWS ECS Fargate
REM  
REM  Prerequisites:
REM    1. AWS CLI installed and configured (aws configure)
REM    2. Docker installed
REM    3. Update REGION and ACCOUNT_ID below
REM ============================================================

SET REGION=ap-south-1
SET ACCOUNT_ID=YOUR_AWS_ACCOUNT_ID
SET REPO_NAME=incident-commander
SET CLUSTER_NAME=incident-commander-cluster
SET SERVICE_NAME=incident-commander-service
SET IMAGE_URI=%ACCOUNT_ID%.dkr.ecr.%REGION%.amazonaws.com/%REPO_NAME%:latest

echo.
echo ============================================================
echo  STEP 1: Create ECR Repository
echo ============================================================
aws ecr create-repository --repository-name %REPO_NAME% --region %REGION% 2>nul
echo Done.

echo.
echo ============================================================
echo  STEP 2: Login to ECR
echo ============================================================
aws ecr get-login-password --region %REGION% | docker login --username AWS --password-stdin %ACCOUNT_ID%.dkr.ecr.%REGION%.amazonaws.com
echo Done.

echo.
echo ============================================================
echo  STEP 3: Build Docker Image
echo ============================================================
docker build -t %REPO_NAME% .
echo Done.

echo.
echo ============================================================
echo  STEP 4: Tag and Push Image
echo ============================================================
docker tag %REPO_NAME%:latest %IMAGE_URI%
docker push %IMAGE_URI%
echo Done.

echo.
echo ============================================================
echo  STEP 5: Store API Key in SSM Parameter Store
echo ============================================================
echo Enter your OpenAI API Key:
set /p API_KEY=
aws ssm put-parameter --name "/incident-commander/OPENAI_API_KEY" --type "SecureString" --value "%API_KEY%" --region %REGION% --overwrite
echo Done.

echo.
echo ============================================================
echo  STEP 6: Create CloudWatch Log Group
echo ============================================================
aws logs create-log-group --log-group-name /ecs/incident-commander --region %REGION% 2>nul
echo Done.

echo.
echo ============================================================
echo  STEP 7: Create ECS Cluster
echo ============================================================
aws ecs create-cluster --cluster-name %CLUSTER_NAME% --region %REGION%
echo Done.

echo.
echo ============================================================
echo  STEP 8: Register Task Definition
echo ============================================================
REM Replace placeholders in task definition
powershell -Command "(Get-Content aws\ecs-task-definition.json) -replace '<AWS_ACCOUNT_ID>','%ACCOUNT_ID%' -replace '<REGION>','%REGION%' | Set-Content aws\ecs-task-definition-deploy.json"
aws ecs register-task-definition --cli-input-json file://aws/ecs-task-definition-deploy.json --region %REGION%
echo Done.

echo.
echo ============================================================
echo  STEP 9: Create ECS Service (with public IP)
echo ============================================================
echo.
echo NOTE: You need a VPC with public subnets and a security group
echo       that allows inbound traffic on port 8000.
echo.
echo Enter your Subnet ID (e.g., subnet-abc123):
set /p SUBNET_ID=
echo Enter your Security Group ID (e.g., sg-abc123):
set /p SG_ID=

aws ecs create-service ^
  --cluster %CLUSTER_NAME% ^
  --service-name %SERVICE_NAME% ^
  --task-definition incident-commander ^
  --desired-count 1 ^
  --launch-type FARGATE ^
  --network-configuration "awsvpcConfiguration={subnets=[%SUBNET_ID%],securityGroups=[%SG_ID%],assignPublicIp=ENABLED}" ^
  --region %REGION%

echo.
echo ============================================================
echo  DEPLOYMENT COMPLETE!
echo ============================================================
echo.
echo Your service is deploying. Check status:
echo   aws ecs describe-services --cluster %CLUSTER_NAME% --services %SERVICE_NAME% --region %REGION%
echo.
echo Once running, find the public IP:
echo   aws ecs list-tasks --cluster %CLUSTER_NAME% --region %REGION%
echo   aws ecs describe-tasks --cluster %CLUSTER_NAME% --tasks TASK_ARN --region %REGION%
echo.
echo Then open: http://PUBLIC_IP:8000/dashboard
echo.
pause
