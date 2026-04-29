#!/usr/bin/env bash
set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
INSTANCE_NAME="${INSTANCE_NAME:-cs551-llm-ec2}"
INSTANCE_TYPE="${INSTANCE_TYPE:-t3.small}"
KEY_NAME="${KEY_NAME:-cs551-llm-ec2-key}"
SECURITY_GROUP_NAME="${SECURITY_GROUP_NAME:-cs551-llm-ec2-sg}"
SSH_CIDR="${SSH_CIDR:-0.0.0.0/0}"
APP_CIDR="${APP_CIDR:-0.0.0.0/0}"
KEY_OUTPUT_PATH="${KEY_OUTPUT_PATH:-deploy/llm_vm/.keys/${KEY_NAME}.pem}"

export AWS_REGION AWS_DEFAULT_REGION="${AWS_REGION}"

echo "[ec2] resolving default VPC + subnet in ${AWS_REGION}"
VPC_ID="$(aws ec2 describe-vpcs \
  --region "${AWS_REGION}" \
  --filters Name=isDefault,Values=true \
  --query 'Vpcs[0].VpcId' \
  --output text)"

SUBNET_ID="$(aws ec2 describe-subnets \
  --region "${AWS_REGION}" \
  --filters Name=vpc-id,Values="${VPC_ID}" Name=default-for-az,Values=true \
  --query 'Subnets[0].SubnetId' \
  --output text)"

AMI_ID="$(aws ssm get-parameter \
  --region "${AWS_REGION}" \
  --name /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 \
  --query 'Parameter.Value' \
  --output text)"

echo "[ec2] ensuring security group ${SECURITY_GROUP_NAME}"
SG_ID="$(aws ec2 describe-security-groups \
  --region "${AWS_REGION}" \
  --filters Name=group-name,Values="${SECURITY_GROUP_NAME}" Name=vpc-id,Values="${VPC_ID}" \
  --query 'SecurityGroups[0].GroupId' \
  --output text)"

if [[ "${SG_ID}" == "None" ]]; then
  SG_ID="$(aws ec2 create-security-group \
    --region "${AWS_REGION}" \
    --group-name "${SECURITY_GROUP_NAME}" \
    --description "CS551 LLM EC2 SG" \
    --vpc-id "${VPC_ID}" \
    --query 'GroupId' \
    --output text)"
fi

aws ec2 authorize-security-group-ingress \
  --region "${AWS_REGION}" \
  --group-id "${SG_ID}" \
  --ip-permissions "[{\"IpProtocol\":\"tcp\",\"FromPort\":22,\"ToPort\":22,\"IpRanges\":[{\"CidrIp\":\"${SSH_CIDR}\",\"Description\":\"ssh\"}]},{\"IpProtocol\":\"tcp\",\"FromPort\":5003,\"ToPort\":5003,\"IpRanges\":[{\"CidrIp\":\"${APP_CIDR}\",\"Description\":\"llm-api\"}]}]" \
  >/dev/null 2>&1 || true

mkdir -p "$(dirname "${KEY_OUTPUT_PATH}")"
chmod 700 "$(dirname "${KEY_OUTPUT_PATH}")"

echo "[ec2] ensuring key pair ${KEY_NAME}"
if ! aws ec2 describe-key-pairs --region "${AWS_REGION}" --key-names "${KEY_NAME}" >/dev/null 2>&1; then
  aws ec2 create-key-pair \
    --region "${AWS_REGION}" \
    --key-name "${KEY_NAME}" \
    --query 'KeyMaterial' \
    --output text > "${KEY_OUTPUT_PATH}"
  chmod 600 "${KEY_OUTPUT_PATH}"
fi

echo "[ec2] launching instance ${INSTANCE_NAME}"
INSTANCE_ID="$(aws ec2 run-instances \
  --region "${AWS_REGION}" \
  --image-id "${AMI_ID}" \
  --instance-type "${INSTANCE_TYPE}" \
  --key-name "${KEY_NAME}" \
  --security-group-ids "${SG_ID}" \
  --subnet-id "${SUBNET_ID}" \
  --associate-public-ip-address \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=${INSTANCE_NAME}}]" \
  --query 'Instances[0].InstanceId' \
  --output text)"

echo "[ec2] waiting for instance health checks"
aws ec2 wait instance-status-ok --region "${AWS_REGION}" --instance-ids "${INSTANCE_ID}"

PUBLIC_IP="$(aws ec2 describe-instances \
  --region "${AWS_REGION}" \
  --instance-ids "${INSTANCE_ID}" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)"

cat <<EOF
[ec2] provisioned
INSTANCE_ID=${INSTANCE_ID}
PUBLIC_IP=${PUBLIC_IP}
KEY_PATH=${KEY_OUTPUT_PATH}
EOF
