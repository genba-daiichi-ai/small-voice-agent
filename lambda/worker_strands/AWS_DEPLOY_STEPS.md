# AWS Console deployment steps

## 0. Safe rollback preparation

1. Open **AWS Console**.
2. Confirm the Region at the top right is **Asia Pacific (Tokyo) ap-northeast-1**.
3. Open **Lambda**.
4. Select **SmallVoiceWorkerFunction**.
5. Open **Code**.
6. Choose **Actions → Export function → Download deployment package**.
7. Save the current ZIP as `SmallVoiceWorkerFunction_BEFORE_STRANDS.zip`.

## 1. Confirm runtime and architecture

1. In the same function, open **Configuration**.
2. Open **Runtime settings**.
3. Confirm the runtime is **Python 3.13**.
4. Confirm **Architecture** is `x86_64`.
5. Confirm timeout is at least **60 seconds** and memory is at least **512 MB**. If lower, choose **Edit**, set them, and save. These settings affect only the Worker.

## 2. Add the official Strands layer

1. Open the **Code** tab.
2. Scroll to **Layers**.
3. Choose **Add a layer**.
4. Choose **Specify an ARN**.
5. Paste the ARN verified in the live Worker:
   `arn:aws:lambda:ap-northeast-1:856699698935:layer:strands-agents-py3_13-x86_64:2`
6. Choose **Verify** and confirm `strands-agents v1.40.0`, Python 3.13, and x86_64.
7. Choose **Verify**, then **Add**.

Do not substitute a Python 3.12 or arm64 layer for this verified configuration.

## 3. Upload the Worker ZIP

1. Stay at **Lambda → SmallVoiceWorkerFunction → Code**.
2. Choose **Upload from**.
3. Choose **.zip file**.
4. Choose **Upload** and select `SmallVoiceWorkerFunction_STRANDS_FINAL.zip`.
5. Choose **Save**.
6. Choose **Deploy** if the button is shown.
7. Open **Configuration → Runtime settings → Edit**.
8. Set Handler to `lambda_function.lambda_handler`.
9. Choose **Save**.

## 4. Environment variables

1. Open **Configuration → Environment variables**.
2. If the function already has table/model variables, keep them unchanged.
3. If none exist, no addition is required because the code defaults to `SmallVoiceReports`, `amazon.nova-lite-v1:0`, and `small-voice-v01`.
4. Only if your existing tenant differs, add `DEFAULT_TENANT_ID` with the exact current tenant value.

## 5. IAM check

1. Open **Configuration → Permissions**.
2. Select the execution role name.
3. Confirm the role already allows `dynamodb:GetItem`, `dynamodb:UpdateItem`, CloudWatch Logs writes, and `bedrock:InvokeModel`.
4. Because Nova Lite already worked in this function, do not change IAM unless CloudWatch shows `AccessDeniedException`.
5. If `bedrock:InvokeModel` is missing, add an inline policy scoped to:
   `arn:aws:bedrock:ap-northeast-1::foundation-model/amazon.nova-lite-v1:0`

## 6. SQS trigger check

1. Return to **Lambda → SmallVoiceWorkerFunction**.
2. In **Function overview**, select the SQS trigger.
3. Confirm it is **Enabled** and points to the existing main queue.
4. Do not recreate the queue, trigger, retry policy, or DLQ.

## 7. Live test

1. Open the existing Amplify public URL.
2. Submit CASE 1 from `TEST_CASES.md`.
3. Wait for `Processing complete`.
4. Confirm the page shows the Agent result and **Human review required**.
5. Open **DynamoDB → Tables → SmallVoiceReports → Explore table items**.
6. Open the new report and confirm:
   - `processing_status = DONE`
   - `agent_result_text` is present
   - `bedrock_model = amazon.nova-lite-v1:0`
   - `worker_finished_at` is present
7. Open **SQS**, confirm the main queue has 0 available messages after processing and DLQ has 0.

## 8. If it fails

1. Open **Lambda → SmallVoiceWorkerFunction → Monitor → View CloudWatch logs**.
2. Open the newest log stream.
3. If `No module named strands`, recheck the Layer ARN and architecture.
4. If `AccessDeniedException`, check the IAM step above.
5. If `Report not found`, compare the SQS body keys with `tenant_id`, `entity_key`, and `report_id`.
6. To roll back, remove the Strands layer and upload `SmallVoiceWorkerFunction_BEFORE_STRANDS.zip`.
