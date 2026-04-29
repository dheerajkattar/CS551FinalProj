# LLM Kubernetes Deployment (EKS + GKE)

This directory contains shared Kubernetes manifests and cloud-specific overlays for running the LLM app on EKS and GKE.

## Layout

- `base/`:
  - shared namespace, deployment, service, config, HPA, and PDB.
- `overlays/eks/`:
  - AWS ALB ingress + provider config patch.
- `overlays/gke/`:
  - GKE ingress + provider config patch.
- `scripts/`:
  - provisioning, deployment, and verification helpers.

## Prerequisites

- AWS CLI + `eksctl` configured for target account.
- `gcloud` CLI configured for target project.
- `kubectl` and `kustomize`.
- Container image pushed to a registry accessible by both clusters.

## Provisioning flow

1. Provision EKS + ElastiCache Redis:
   - `bash deploy/llm_k8s/scripts/provision_eks.sh`
2. Provision GKE + Memorystore Redis:
   - `PROJECT_ID=<project-id> bash deploy/llm_k8s/scripts/provision_gke.sh`

## Deployment flow

1. Create/update Kubernetes secret with `GEMINI_API_KEY` and `REDIS_URL`.
2. Deploy EKS overlay:
   - `IMAGE_REPO=<registry/image> IMAGE_TAG=<tag> bash deploy/llm_k8s/scripts/deploy.sh eks`
3. Deploy GKE overlay:
   - `IMAGE_REPO=<registry/image> IMAGE_TAG=<tag> bash deploy/llm_k8s/scripts/deploy.sh gke`

## Verification

- Verify endpoint health and session continuity:
  - `bash deploy/llm_k8s/scripts/verify_endpoints.sh <eks-url> <gke-url>`
- Export runtime config for parity checks:
  - `bash deploy/llm_k8s/scripts/export_runtime_config.sh llm_runtime_config.json`
