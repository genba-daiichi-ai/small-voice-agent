# Small Voice Agent — Strands Agents SDK update

Small Voice Agent now uses the **Strands Agents SDK** in its live worker implementation. `SmallVoiceWorkerFunction` creates a Strands `Agent` with `BedrockModel`, and the Agent invokes **Amazon Nova Lite** on Amazon Bedrock in `ap-northeast-1`.

```python
from strands import Agent
from strands.models import BedrockModel

model = BedrockModel(
    model_id="amazon.nova-lite-v1:0",
    region_name="ap-northeast-1",
    streaming=False,
)
agent = Agent(model=model, system_prompt=SYSTEM_PROMPT, tools=[])
result = agent(prompt)
```

## Existing asynchronous architecture

`AWS Amplify → API Gateway → Submit Lambda → DynamoDB → SQS → SmallVoiceWorkerFunction (Strands Agents SDK) → Amazon Bedrock / Nova Lite → DynamoDB → Status Lambda → Web UI`

The update does not introduce a new frontend, API, database, AgentCore runtime, RAG, vector database, or multi-agent design. It replaces only the worker's direct model invocation.

## Human review required

The Agent structures a workplace concern as a proposal. It does not select a final answer, change workplace rules, rank people, or make safety, medical, disciplinary, or quality decisions. The UI continues to display **Human review required**. A person verifies facts and decides what happens next.

## Processing states and stored evidence

The existing durable state contract is preserved:

- `PROCESSING` when the worker starts;
- `DONE` when `agent_result_text`, `bedrock_model`, and `worker_finished_at` are stored;
- `FAILED` when Agent processing fails.

The worker accepts the current composite DynamoDB key (`tenant_id`, `entity_key`) and SQS messages containing `entity_key` or `report_id`. Duplicate deliveries already in `DONE` state are skipped.

## Setup

- AWS Region: `ap-northeast-1`
- Lambda runtime: Python 3.13 (verified live)
- Architecture: x86_64 (verified live)
- Handler: `lambda_function.lambda_handler`
- Model: `amazon.nova-lite-v1:0`
- DynamoDB table: `SmallVoiceReports`
- Official Strands layer used by the live Worker:
  `arn:aws:lambda:ap-northeast-1:856699698935:layer:strands-agents-py3_13-x86_64:2`

Environment variables are optional because existing names are the defaults:

| Variable | Default |
|---|---|
| `TABLE_NAME` | `SmallVoiceReports` |
| `BEDROCK_MODEL_ID` | `amazon.nova-lite-v1:0` |
| `DEFAULT_TENANT_ID` | `small-voice-v01` |
| `LOG_LEVEL` | `INFO` |

## IAM

Keep the existing DynamoDB and CloudWatch Logs permissions. Because the worker uses non-streaming inference, the existing `bedrock:InvokeModel` permission for Nova Lite is sufficient. Do not add `bedrock:InvokeModelWithResponseStream` unless streaming is enabled later.

Minimum Bedrock statement:

```json
{
  "Effect": "Allow",
  "Action": "bedrock:InvokeModel",
  "Resource": "arn:aws:bedrock:ap-northeast-1::foundation-model/amazon.nova-lite-v1:0"
}
```

The role also needs `dynamodb:GetItem` and `dynamodb:UpdateItem` for the existing `SmallVoiceReports` table. SQS invocation permissions remain managed by the existing Lambda event source mapping.

## Deploy and test

1. Back up the current worker code.
2. Confirm runtime Python 3.13 and architecture x86_64.
3. Add the matching official Strands layer ARN above.
4. Upload `SmallVoiceWorkerFunction_STRANDS_FINAL.zip` and deploy.
5. Submit one test from the public Web UI.
6. Confirm `PROCESSING → DONE`, result text, model ID, finish timestamp, main queue 0, and DLQ 0.

See `AWS_DEPLOY_STEPS.md` and `TEST_CASES.md` for the exact console workflow and three acceptance tests.
