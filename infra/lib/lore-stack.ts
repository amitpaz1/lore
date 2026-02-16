import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecs_patterns from 'aws-cdk-lib/aws-ecs-patterns';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as cr from 'aws-cdk-lib/custom-resources';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';

/** Environment-specific sizing */
const ENV_CONFIG: Record<string, { cpu: number; memory: number; desiredCount: number; instanceType: string; dbAllocatedStorage: number }> = {
  staging: {
    cpu: 256,
    memory: 512,
    desiredCount: 1,
    instanceType: 't3.micro',
    dbAllocatedStorage: 20,
  },
  production: {
    cpu: 1024,
    memory: 2048,
    desiredCount: 2,
    instanceType: 't3.small',
    dbAllocatedStorage: 50,
  },
};

export interface LoreStackProps extends cdk.StackProps {
  envName: string;
}

export class LoreStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: LoreStackProps) {
    super(scope, id, props);

    const config = ENV_CONFIG[props.envName] || ENV_CONFIG['staging'];
    const prefix = `lore-${props.envName}`;

    // ── VPC ────────────────────────────────────────────────────────
    const vpc = new ec2.Vpc(this, 'Vpc', {
      maxAzs: 2,
      natGateways: props.envName === 'production' ? 2 : 1,
      vpcName: `${prefix}-vpc`,
    });

    // ── Security Groups ────────────────────────────────────────────
    const albSg = new ec2.SecurityGroup(this, 'AlbSg', {
      vpc,
      description: 'ALB security group',
      allowAllOutbound: true,
    });
    albSg.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(80), 'HTTP');
    albSg.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(443), 'HTTPS');

    const ecsSg = new ec2.SecurityGroup(this, 'EcsSg', {
      vpc,
      description: 'ECS tasks security group',
      allowAllOutbound: true,
    });
    ecsSg.addIngressRule(albSg, ec2.Port.tcp(8765), 'ALB to ECS');

    const dbSg = new ec2.SecurityGroup(this, 'DbSg', {
      vpc,
      description: 'RDS security group',
      allowAllOutbound: false,
    });
    dbSg.addIngressRule(ecsSg, ec2.Port.tcp(5432), 'ECS to RDS');

    // ── Secrets Manager ────────────────────────────────────────────
    const dbSecret = new secretsmanager.Secret(this, 'DbSecret', {
      secretName: `${prefix}/database-credentials`,
      generateSecretString: {
        secretStringTemplate: JSON.stringify({ username: 'lore' }),
        generateStringKey: 'password',
        excludePunctuation: true,
        passwordLength: 32,
      },
    });

    const rootKeySecret = new secretsmanager.Secret(this, 'RootKeySecret', {
      secretName: `${prefix}/lore-root-key`,
      generateSecretString: {
        excludePunctuation: false,
        passwordLength: 48,
      },
    });

    // ── RDS Postgres (pgvector) ────────────────────────────────────
    const dbInstance = new rds.DatabaseInstance(this, 'Database', {
      engine: rds.DatabaseInstanceEngine.postgres({
        version: rds.PostgresEngineVersion.VER_16_4,
      }),
      instanceType: ec2.InstanceType.of(
        ec2.InstanceClass.T3,
        props.envName === 'production' ? ec2.InstanceSize.SMALL : ec2.InstanceSize.MICRO,
      ),
      vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      securityGroups: [dbSg],
      credentials: rds.Credentials.fromSecret(dbSecret),
      databaseName: 'lore',
      allocatedStorage: config.dbAllocatedStorage,
      maxAllocatedStorage: config.dbAllocatedStorage * 2,
      multiAz: props.envName === 'production',
      deletionProtection: props.envName === 'production',
      removalPolicy: props.envName === 'production'
        ? cdk.RemovalPolicy.RETAIN
        : cdk.RemovalPolicy.DESTROY,
      backupRetention: cdk.Duration.days(props.envName === 'production' ? 14 : 1),
    });

    // ── pgvector extension via Custom Resource (Lambda) ────────────
    // Allow the Lambda in the VPC to reach RDS
    const pgvectorInitSg = new ec2.SecurityGroup(this, 'PgvectorInitSg', {
      vpc,
      description: 'Lambda for pgvector init',
      allowAllOutbound: true,
    });
    dbSg.addIngressRule(pgvectorInitSg, ec2.Port.tcp(5432), 'Lambda pgvector init');

    const pgvectorInitFn = new lambda.Function(this, 'PgvectorInitFn', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'index.handler',
      code: lambda.Code.fromInline(`
import json
import boto3
import urllib3

http = urllib3.PoolManager()

def send_response(event, context, status, reason=""):
    body = json.dumps({
        "Status": status,
        "Reason": reason or "See CloudWatch",
        "PhysicalResourceId": context.log_stream_name,
        "StackId": event["StackId"],
        "RequestId": event["RequestId"],
        "LogicalResourceId": event["LogicalResourceId"],
    })
    http.request("PUT", event["ResponseURL"], body=body.encode(),
                 headers={"Content-Type": ""})

def handler(event, context):
    if event["RequestType"] == "Delete":
        send_response(event, context, "SUCCESS")
        return
    try:
        import subprocess, sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary", "-t", "/tmp/deps", "-q"])
        sys.path.insert(0, "/tmp/deps")
        import psycopg2

        sm = boto3.client("secretsmanager")
        secret = json.loads(sm.get_secret_value(SecretId=event["ResourceProperties"]["SecretArn"])["SecretString"])
        conn = psycopg2.connect(
            host=event["ResourceProperties"]["Host"],
            port=5432,
            user=secret["username"],
            password=secret["password"],
            dbname=event["ResourceProperties"]["DbName"],
        )
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur.close()
        conn.close()
        send_response(event, context, "SUCCESS", "pgvector enabled")
    except Exception as e:
        send_response(event, context, "FAILED", str(e))
`),
      timeout: cdk.Duration.minutes(5),
      memorySize: 256,
      vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      securityGroups: [pgvectorInitSg],
      logRetention: logs.RetentionDays.ONE_WEEK,
    });

    dbSecret.grantRead(pgvectorInitFn);

    const pgvectorInit = new cdk.CustomResource(this, 'PgvectorInit', {
      serviceToken: pgvectorInitFn.functionArn,
      properties: {
        SecretArn: dbSecret.secretArn,
        Host: dbInstance.dbInstanceEndpointAddress,
        DbName: 'lore',
      },
    });
    pgvectorInit.node.addDependency(dbInstance);

    // ── ECS Cluster ────────────────────────────────────────────────
    const cluster = new ecs.Cluster(this, 'Cluster', {
      vpc,
      clusterName: `${prefix}-cluster`,
      containerInsights: props.envName === 'production',
    });

    // ── DATABASE_URL secret (composite) ────────────────────────────
    // Build DATABASE_URL from RDS endpoint + credentials
    const databaseUrlSecret = new secretsmanager.Secret(this, 'DatabaseUrlSecret', {
      secretName: `${prefix}/database-url`,
      secretStringValue: cdk.SecretValue.unsafePlainText(
        // At deploy time this resolves; the ECS task reads the secret at runtime
        `postgresql://${dbSecret.secretValueFromJson('username').unsafeUnwrap()}:${dbSecret.secretValueFromJson('password').unsafeUnwrap()}@${dbInstance.dbInstanceEndpointAddress}:${dbInstance.dbInstanceEndpointPort}/lore`
      ),
    });

    // ── Fargate Service + ALB ──────────────────────────────────────
    const taskRole = new iam.Role(this, 'TaskRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      roleName: `${prefix}-task-role`,
    });

    const fargateService = new ecs_patterns.ApplicationLoadBalancedFargateService(this, 'Service', {
      cluster,
      serviceName: `${prefix}-service`,
      cpu: config.cpu,
      memoryLimitMiB: config.memory,
      desiredCount: config.desiredCount,
      taskImageOptions: {
        // In CI/CD, build and push to ECR, then pass the image URI via context:
        //   cdk deploy --context env=production --context imageUri=123456.dkr.ecr...
        // For local dev, falls back to a placeholder; actual deploy requires imageUri.
        image: ecs.ContainerImage.fromRegistry(
          scope.node.tryGetContext('imageUri') || 'public.ecr.aws/docker/library/python:3.11-slim'
        ),
        containerPort: 8765,
        taskRole,
        secrets: {
          DATABASE_URL: ecs.Secret.fromSecretsManager(databaseUrlSecret),
          LORE_ROOT_KEY: ecs.Secret.fromSecretsManager(rootKeySecret),
        },
        environment: {
          LORE_ENV: props.envName,
        },
        logDriver: ecs.LogDrivers.awsLogs({
          streamPrefix: prefix,
          logRetention: logs.RetentionDays.TWO_WEEKS,
        }),
      },
      publicLoadBalancer: true,
      securityGroups: [ecsSg],
      assignPublicIp: false,
      taskSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
    });

    // Override ALB SG
    fargateService.loadBalancer.addSecurityGroup(albSg);

    // Health checks
    fargateService.targetGroup.configureHealthCheck({
      path: '/health',
      healthyHttpCodes: '200',
      interval: cdk.Duration.seconds(30),
      timeout: cdk.Duration.seconds(5),
      healthyThresholdCount: 2,
      unhealthyThresholdCount: 3,
    });

    // ECS readiness — container health check
    fargateService.taskDefinition.defaultContainer!.addContainerDependencies();

    // Ensure pgvector is ready before ECS tasks start
    fargateService.node.addDependency(pgvectorInit);

    // ── Outputs ────────────────────────────────────────────────────
    new cdk.CfnOutput(this, 'AlbDns', {
      value: fargateService.loadBalancer.loadBalancerDnsName,
      description: 'ALB DNS name',
    });

    new cdk.CfnOutput(this, 'DbEndpoint', {
      value: dbInstance.dbInstanceEndpointAddress,
      description: 'RDS endpoint',
    });
  }
}
