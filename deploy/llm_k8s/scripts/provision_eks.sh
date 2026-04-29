#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="${CLUSTER_NAME:-cs551-llm-eks}"
REGION="${REGION:-us-east-1}"
NODE_TYPE="${NODE_TYPE:-t3.large}"
NODE_COUNT="${NODE_COUNT:-2}"
REDIS_NAME="${REDIS_NAME:-cs551-llm-redis}"
REDIS_NODE_TYPE="${REDIS_NODE_TYPE:-cache.t4g.small}"
REDIS_ENGINE_VERSION="${REDIS_ENGINE_VERSION:-7.1}"
FORCE_RECREATE_CLUSTER="${FORCE_RECREATE_CLUSTER:-false}"
DEBUG_LOG_PATH="/Users/ndkat/Projects/CS551/CS551FinalProj/.cursor/debug-b2f02b.log"
DEBUG_RUN_ID="${DEBUG_RUN_ID:-pre-fix}"

# #region agent log
debug_log() {
  local hypothesis_id="$1"
  local location="$2"
  local message="$3"
  local data_raw="${4:-}"
  python3 - "$DEBUG_LOG_PATH" "$DEBUG_RUN_ID" "$hypothesis_id" "$location" "$message" "$data_raw" <<'PY'
import json
import sys
import time

path, run_id, hypothesis_id, location, message, data_raw = sys.argv[1:]
payload = {
    "sessionId": "b2f02b",
    "runId": run_id,
    "hypothesisId": hypothesis_id,
    "location": location,
    "message": message,
    "data": {"details": data_raw},
    "timestamp": int(time.time() * 1000),
}
with open(path, "a", encoding="utf-8") as fh:
    fh.write(json.dumps(payload, separators=(",", ":")) + "\n")
PY
}
# #endregion

# #region agent log
on_eksctl_error() {
  local exit_code="$?"
  local nodegroup_stack="eksctl-${CLUSTER_NAME}-nodegroup-llm-workers"
  local cluster_stack="eksctl-${CLUSTER_NAME}-cluster"
  debug_log "H0" "provision_eks.sh:on_eksctl_error" "eksctl_failed" "exitCode=${exit_code}; cluster=${CLUSTER_NAME}; region=${REGION}"

  local stack_status
  stack_status="$(aws cloudformation describe-stacks --region "${REGION}" --stack-name "${nodegroup_stack}" --query 'Stacks[0].StackStatus' --output text 2>/dev/null || true)"
  debug_log "H1" "provision_eks.sh:on_eksctl_error" "nodegroup_stack_status" "stack=${nodegroup_stack}; status=${stack_status}"

  local failed_event
  failed_event="$(aws cloudformation describe-stack-events --region "${REGION}" --stack-name "${nodegroup_stack}" --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`]|[0].ResourceStatusReason' --output text 2>/dev/null || true)"
  debug_log "H2" "provision_eks.sh:on_eksctl_error" "nodegroup_first_create_failed_reason" "stack=${nodegroup_stack}; reason=${failed_event}"

  local cluster_failed_event
  cluster_failed_event="$(aws cloudformation describe-stack-events --region "${REGION}" --stack-name "${cluster_stack}" --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`]|[0].ResourceStatusReason' --output text 2>/dev/null || true)"
  debug_log "H4" "provision_eks.sh:on_eksctl_error" "cluster_first_create_failed_reason" "stack=${cluster_stack}; reason=${cluster_failed_event}"

  local cluster_stack_status
  cluster_stack_status="$(aws cloudformation describe-stacks --region "${REGION}" --stack-name "${cluster_stack}" --query 'Stacks[0].StackStatus' --output text 2>/dev/null || true)"
  debug_log "H11" "provision_eks.sh:on_eksctl_error" "cluster_stack_status_at_error" "stack=${cluster_stack}; status=${cluster_stack_status}"

  local nodegroup_status
  nodegroup_status="$(aws eks describe-nodegroup --region "${REGION}" --cluster-name "${CLUSTER_NAME}" --nodegroup-name "llm-workers" --query 'nodegroup.status' --output text 2>/dev/null || true)"
  debug_log "H5" "provision_eks.sh:on_eksctl_error" "eks_nodegroup_status" "cluster=${CLUSTER_NAME}; nodegroup=llm-workers; status=${nodegroup_status}"

  local nodegroup_health_issues
  nodegroup_health_issues="$(aws eks describe-nodegroup --region "${REGION}" --cluster-name "${CLUSTER_NAME}" --nodegroup-name "llm-workers" --query 'nodegroup.health.issues[*].code' --output text 2>/dev/null || true)"
  debug_log "H6" "provision_eks.sh:on_eksctl_error" "eks_nodegroup_health_issue_codes" "cluster=${CLUSTER_NAME}; nodegroup=llm-workers; issues=${nodegroup_health_issues}"

  local nodegroup_resources
  nodegroup_resources="$(aws cloudformation describe-stack-resources --region "${REGION}" --stack-name "${nodegroup_stack}" --query 'StackResources[*].[LogicalResourceId,ResourceType,ResourceStatus,ResourceStatusReason]' --output text 2>/dev/null || true)"
  debug_log "H8" "provision_eks.sh:on_eksctl_error" "nodegroup_stack_resources_status" "stack=${nodegroup_stack}; resources=${nodegroup_resources}"

  local asg_name
  asg_name="$(aws eks describe-nodegroup --region "${REGION}" --cluster-name "${CLUSTER_NAME}" --nodegroup-name "llm-workers" --query 'nodegroup.resources.autoScalingGroups[0].name' --output text 2>/dev/null || true)"
  debug_log "H9" "provision_eks.sh:on_eksctl_error" "nodegroup_asg_name" "cluster=${CLUSTER_NAME}; nodegroup=llm-workers; asg=${asg_name}"

  local asg_activities
  asg_activities="$(aws autoscaling describe-scaling-activities --region "${REGION}" --auto-scaling-group-name "${asg_name}" --max-items 5 --query 'Activities[*].[StatusCode,Description,Cause,StatusMessage]' --output text 2>/dev/null || true)"
  debug_log "H10" "provision_eks.sh:on_eksctl_error" "nodegroup_asg_recent_activities" "asg=${asg_name}; activities=${asg_activities}"
}
# #endregion

# #region agent log
wait_for_stack_name_release() {
  local stack_name="$1"
  local max_wait_seconds=300
  local sleep_seconds=10
  local elapsed=0

  while (( elapsed < max_wait_seconds )); do
    local stack_status
    stack_status="$(aws cloudformation describe-stacks --region "${REGION}" --stack-name "${stack_name}" --query 'Stacks[0].StackStatus' --output text 2>/dev/null || true)"
    debug_log "H12" "provision_eks.sh:wait_for_stack_name_release" "post_delete_cluster_stack_status_poll" "stack=${stack_name}; elapsed=${elapsed}; status=${stack_status}"
    if [[ -z "${stack_status}" || "${stack_status}" == "None" ]]; then
      debug_log "H12" "provision_eks.sh:wait_for_stack_name_release" "post_delete_cluster_stack_name_released" "stack=${stack_name}; elapsed=${elapsed}"
      return 0
    fi
    sleep "${sleep_seconds}"
    elapsed=$((elapsed + sleep_seconds))
  done

  debug_log "H13" "provision_eks.sh:wait_for_stack_name_release" "post_delete_cluster_stack_name_still_reserved" "stack=${stack_name}; waited=${max_wait_seconds}"
  return 1
}
# #endregion

# #region agent log
ensure_cluster_name_available() {
  local cluster_stack="eksctl-${CLUSTER_NAME}-cluster"
  local stack_status
  stack_status="$(aws cloudformation describe-stacks --region "${REGION}" --stack-name "${cluster_stack}" --query 'Stacks[0].StackStatus' --output text 2>/dev/null || true)"

  if [[ -n "${stack_status}" && "${stack_status}" != "None" ]]; then
    debug_log "H7" "provision_eks.sh:ensure_cluster_name_available" "cluster_stack_already_exists" "stack=${cluster_stack}; status=${stack_status}; forceRecreate=${FORCE_RECREATE_CLUSTER}"
    if [[ "${FORCE_RECREATE_CLUSTER}" == "true" ]]; then
      echo "[eks] existing cluster stack detected (${cluster_stack}:${stack_status}), deleting cluster before recreate"
      eksctl delete cluster --region "${REGION}" --name "${CLUSTER_NAME}" || true
      wait_for_stack_name_release "${cluster_stack}" || {
        echo "[eks] cluster stack name is still reserved after waiting, aborting recreate."
        exit 1
      }
    else
      echo "[eks] cluster stack already exists (${cluster_stack}:${stack_status})."
      echo "[eks] run 'eksctl delete cluster --region=${REGION} --name=${CLUSTER_NAME}' first, or rerun with FORCE_RECREATE_CLUSTER=true."
      exit 1
    fi
  else
    debug_log "H7" "provision_eks.sh:ensure_cluster_name_available" "cluster_stack_name_free" "stack=${cluster_stack}; status=${stack_status}"
  fi
}
# #endregion

cat <<EOF
[eks] provisioning summary
  cluster: ${CLUSTER_NAME}
  region: ${REGION}
  node type/count: ${NODE_TYPE} x ${NODE_COUNT}
  redis: ${REDIS_NAME} (${REDIS_NODE_TYPE})
EOF

# #region agent log
debug_log "H3" "provision_eks.sh:start" "provision_input" "cluster=${CLUSTER_NAME}; region=${REGION}; nodeType=${NODE_TYPE}; nodeCount=${NODE_COUNT}"
# #endregion

trap on_eksctl_error ERR
ensure_cluster_name_available

eksctl create cluster \
  --name "${CLUSTER_NAME}" \
  --region "${REGION}" \
  --nodegroup-name "llm-workers" \
  --node-type "${NODE_TYPE}" \
  --nodes "${NODE_COUNT}"

aws eks update-kubeconfig --name "${CLUSTER_NAME}" --region "${REGION}"

aws elasticache create-replication-group \
  --region "${REGION}" \
  --replication-group-id "${REDIS_NAME}" \
  --replication-group-description "CS551 LLM benchmark redis" \
  --engine redis \
  --engine-version "${REDIS_ENGINE_VERSION}" \
  --cache-node-type "${REDIS_NODE_TYPE}" \
  --num-node-groups 1 \
  --replicas-per-node-group 0 \
  --automatic-failover-enabled \
  --transit-encryption-enabled \
  --at-rest-encryption-enabled

echo "[eks] finished. ensure AWS Load Balancer Controller is installed before ingress deploy."
