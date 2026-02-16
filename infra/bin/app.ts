#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { LoreStack } from '../lib/lore-stack';

const app = new cdk.App();

const envName = app.node.tryGetContext('env') || 'staging';

new LoreStack(app, `Lore-${envName}`, {
  envName,
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
  },
});
