# Lore CDK Infrastructure

AWS CDK v2 (TypeScript) stack for deploying Lore to AWS with ECS Fargate, ALB, and RDS Postgres (pgvector).

## Architecture

- **VPC** — 2 AZs, public/private subnets, NAT gateway(s)
- **ALB** — Public load balancer, health check on `/health`
- **ECS Fargate** — Runs `Dockerfile.server`, secrets injected from Secrets Manager
- **RDS Postgres 16** — pgvector extension enabled via Lambda custom resource
- **Secrets Manager** — `DATABASE_URL` and `LORE_ROOT_KEY` auto-generated
- **Security Groups** — ALB → ECS (8765), ECS → RDS (5432)

## Environment Parameterization

| Parameter | Staging | Production |
|-----------|---------|------------|
| ECS CPU/Memory | 256/512 | 1024/2048 |
| Desired count | 1 | 2 |
| RDS instance | t3.micro | t3.small |
| Multi-AZ | No | Yes |
| NAT Gateways | 1 | 2 |
| Deletion protection | No | Yes |

## Prerequisites

- Node.js 20+ and npm
- AWS CLI configured with credentials
- CDK bootstrapped: `npx cdk bootstrap aws://ACCOUNT/REGION`

## Setup

```bash
cd infra
npm install
```

## Synth (validate CloudFormation)

```bash
npx cdk synth                                    # staging (default)
npx cdk synth --context env=production            # production
```

## Deploy

> **Note:** Build and push the Docker image to ECR first, then pass `imageUri`.

```bash
# 1. Build & push Docker image
aws ecr get-login-password | docker login --username AWS --password-stdin ACCOUNT.dkr.ecr.REGION.amazonaws.com
docker build -f Dockerfile.server -t lore-server .
docker tag lore-server:latest ACCOUNT.dkr.ecr.REGION.amazonaws.com/lore-server:latest
docker push ACCOUNT.dkr.ecr.REGION.amazonaws.com/lore-server:latest

# 2. Deploy
npx cdk deploy --context env=staging --context imageUri=ACCOUNT.dkr.ecr.REGION.amazonaws.com/lore-server:latest
```

## pgvector Extension

The stack includes a Lambda-backed custom resource that connects to the RDS instance after creation and runs:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

This ensures pgvector is available for the application's vector storage needs. RDS Postgres 16 includes pgvector natively.

## Embedding Model

The embedding model (sentence-transformers/all-MiniLM-L6-v2 via ONNX) is baked into the Docker image at build time. No external model download is needed at runtime. See `Dockerfile.server` and `pyproject.toml` for details.

## Health Checks

- **ALB** → `GET /health` (HTTP 200)
- **ECS container** → Docker HEALTHCHECK hitting `/health`
- **Readiness** → `GET /ready` (application-level readiness)

## Useful Commands

```bash
npx cdk diff                    # Show pending changes
npx cdk deploy                  # Deploy stack
npx cdk destroy                 # Tear down stack
```
