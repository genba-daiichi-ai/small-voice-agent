# Strands live acceptance tests

Run each case from the existing public Web UI. Use synthetic information only.

## CASE 1 — Different senior workers teach the same task in different ways

**入力文**

> 同じ部品の取り付け作業なのに、先輩Aは先に仮締めして位置を合わせ、先輩Bは片側を本締めしてから反対側を締めるように教えます。どちらで覚えればよいのか迷います。

**Context**

> 組立工程。どちらの先輩も長年この作業を担当しています。今のところ不良や事故が起きたという話は聞いていません。

**期待結果**

- 一方を勝手に正解と決めない。
- 共通点、相違点、適用条件を確認対象にする。
- 安全、品質、時間、身体負担などの比較材料を示す。
- 小さな比較確認と、人による判断を提案する。

**DONE確認項目**

- `processing_status = DONE`
- `agent_result_text`に4見出しがある
- `bedrock_model = amazon.nova-lite-v1:0`
- `worker_finished_at`がある
- Web UIに`Processing complete`と`Human review required`がある

## CASE 2 — Repeated reaching across a workbench causes shoulder fatigue

**入力文**

> 作業台の奥にある部品箱へ一日に何度も手を伸ばすため、午後になると肩が重くなります。作業自体は止まっていません。

**Context**

> 立ち作業。部品箱の位置は昔から同じです。安全通路を塞がずに試せる方法を考えたいです。

**期待結果**

- 投稿者の姿勢や体力を責めない。
- 距離、回数、配置、作業条件を事実確認として整理する。
- 健康や安全を断定・診断せず、責任者確認を前提にする。
- 短時間の配置テストや回数記録など、小さな一手を示す。

**DONE確認項目**

CASE 1と同じ5項目を確認する。

## CASE 3 — Temporary storage workaround during a busy period

**入力文**

> 繁忙時間に通常の置き場がいっぱいになると、完成品を別の棚へ一時的に置き、あとで戻しています。作業は終わるので報告されないことが多いです。

**Context**

> 午後の繁忙時間だけ発生します。別の棚には他工程の物が置かれる場合があります。

**期待結果**

- 暫定対応を即座に正解・違反と断定しない。
- 発生時間、頻度、混在、表示、品質・安全ルールを確認対象にする。
- 現場を止めない小さな記録・区分けテストを提案する。
- 最終判断を人へ戻す。

**DONE確認項目**

CASE 1と同じ5項目に加え、SQSメインキュー0、DLQ 0を確認する。
