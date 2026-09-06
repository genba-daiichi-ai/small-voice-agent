# Current-state audit and minimal change set

## Confirmed current state

- The public repository contains the verified architecture and API contract but did not contain the live Worker source.
- The durable contract uses `SmallVoiceReports`, `tenant_id`, `entity_key`, `processing_status`, `agent_result_text`, `bedrock_model`, and `worker_finished_at`.
- The verified live model is `amazon.nova-lite-v1:0` in `ap-northeast-1`.
- The existing path from Amplify through SQS and back to the Web UI is already working and must remain unchanged.

## Four minimal changes

1. Replace only the Worker's direct Bedrock invocation with `Agent` plus `BedrockModel` from the Strands Agents SDK.
2. Preserve SQS input compatibility, DynamoDB keys and attributes, `PROCESSING → DONE / FAILED`, retries, DLQ behavior, and the existing Status Lambda response.
3. Add the official Strands Agents Lambda layer for the Worker's exact Python runtime and architecture; do not introduce AgentCore or new infrastructure.
4. Publish the actual Worker source and update README, architecture, Devpost text, deployment steps, tests, and MIT License so reviewers can verify real Strands use.

## Compatibility boundary

The source supports SQS bodies containing either `entity_key` or `report_id`, plus optional `tenant_id`. Live verification on September 6, 2026 confirmed Python 3.13, x86_64, tenant `small-voice-v01`, the official Strands v1.40.0 layer, successful Web UI completion, DynamoDB `DONE`, stored result/model/timestamps, main queue 0, DLQ 0, and the CloudWatch message `Strands processing DONE`.
