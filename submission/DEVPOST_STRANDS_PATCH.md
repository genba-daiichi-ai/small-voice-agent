# Devpost Strands patch

Use only the following replacement/addition text in the existing submission.

## How we built it

The public interface is hosted on AWS Amplify and sends reports through Amazon API Gateway to a submit Lambda. Each report is stored in Amazon DynamoDB and queued in Amazon SQS. SQS invokes `SmallVoiceWorkerFunction` asynchronously. Inside that worker, I use the Strands Agents SDK to create an `Agent` backed by `BedrockModel`, configured for `amazon.nova-lite-v1:0` in `ap-northeast-1`. The Strands Agent turns the report into a reviewable Japanese proposal and the worker stores the result, model ID, completion time, and durable `DONE` or `FAILED` state in DynamoDB. A status Lambda returns the stored result to the Web UI. The interface keeps “Human review required” visible because the Agent structures options; it does not make the workplace decision.

## Built with

AWS Amplify, Amazon API Gateway, AWS Lambda, Amazon SQS, Amazon DynamoDB, Amazon Bedrock, Amazon Nova Lite, **Strands Agents SDK (Python)**, Amazon CloudWatch, Python, JavaScript, HTML, and CSS.

## Architecture

`AWS Amplify → API Gateway → Submit Lambda → DynamoDB → SQS → SmallVoiceWorkerFunction (Strands Agents SDK) → Amazon Bedrock / Amazon Nova Lite → DynamoDB → Status Lambda → Web UI`

The Strands update is deliberately minimal: the existing public URL, frontend, API contract, queue, table, status polling, and human-review boundary remain unchanged.

## Technical implementation

`SmallVoiceWorkerFunction` imports `Agent` from `strands` and `BedrockModel` from `strands.models`. The model is explicitly configured as `amazon.nova-lite-v1:0` in Tokyo and invoked through the Strands Agent in non-streaming mode. The SQS worker preserves the durable lifecycle `QUEUED → PROCESSING → DONE / FAILED`, writes `agent_result_text`, `bedrock_model`, and `worker_finished_at`, and rethrows failed processing so the existing SQS retry and DLQ path remain active. Duplicate deliveries already marked `DONE` are skipped. No AgentCore migration, RAG, vector database, or multi-agent layer was added.

## Video subtitle additions

Use these lines when the architecture or Worker code is visible:

1. `The live worker now runs on the Strands Agents SDK.`
2. `A Strands Agent uses BedrockModel to invoke Amazon Nova Lite.`
3. `The existing SQS and DynamoDB workflow remains unchanged.`
4. `The Agent produces a proposal. Human review is still required.`

For a Japanese subtitle track:

1. `実働WorkerはStrands Agents SDKを基盤として動作しています。`
2. `Strands AgentがBedrockModel経由でAmazon Nova Liteを呼び出します。`
3. `既存のSQS非同期処理とDynamoDB保存は維持しています。`
4. `AIの出力は提案です。最終判断は人が行います。`
