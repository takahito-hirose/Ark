ARK Core Logic Specification (v0.2.0)
Spec-driven Development — このドキュメントはARKの「聖典（設計書）」である。
すべてのエージェントの実装およびオーケストレーションはこの仕様を絶対遵守しなければならない。

1. Autonomous Loop（自律駆動ループ）
ARKは、単なる一過性の処理ではなく、自己修正と自己学習を備えた閉ループ（Autonomous Loop）として設計される。

┌─────────────────────────────────────────────────────────────┐
│                          USER GOAL                          │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
                     ┌─────────────────┐
                     │  Orchestrator   │  ← State Machine & Memory Manager
                     │  (src/core/)    │
                     └────────┬────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
   ┌─────────────┐   ┌──────────────┐   ┌────────────────┐
   │  PHASE 1    │   │  PHASE 2     │   │  PHASE 3       │
   │  PLAN       │──▶│  CODE        │──▶│  REVIEW        │
   │  Architect  │   │  Coder       │   │  Reviewer      │
   └─────────────┘   └──────────────┘   └────────┬───────┘
         ▲                                        │
         │         ┌──────────────┐               │ PASS
         └─────────│ Circuit      │◀──────────────┘
          FAIL×3   │ Breaker      │               ▼
                   └──────────────┘      ┌─────────────────┐
                                         │  PHASE 4        │
                                         │  COMMIT         │
                                         └────────┬────────┘
                                                  │
                                                  ▼
                                         ┌─────────────────┐
                                         │  PHASE 5        │
                                         │  REFLECT        │ 🚀 NEW!
                                         │  Reflector      │ (Memory Archive)
                                         └─────────────────┘

1.1 フェーズ定義
| Phase | Agent | 入力 | 出力 | 終了条件 |
| :--- | :--- | :--- | :--- | :--- |
| PLAN | Architect | Goal + Tier 2 記憶 | PlanPayload | 実装方針の確定 |
| CODE | Coder | PlanPayload | CodePayload | コード生成（職人品質） |
| REVIEW | Reviewer | CodePayload + Goal | ReviewPayload | status: PASS（掟遵守が最優先） |
| COMMIT | Orchestrator | CodePayload | 成果物 | Gitへの記録と物理ファイル配置 |
| REFLECT | Reflector | Goal + Code | Tier 2/3 への保存 | 知見の永続化（自律学習） |

1.2 State Machine（状態遷移）
IDLE → PLANNING → CODING → REVIEWING → COMMITTING → DONE
                    ↑______________|
                    (FAIL: retry_count < 3)

2. Tiered Memory System（記憶の3層階層化）
ARKは「忘却」と「学習」を制御するために、以下の3層の記憶構造を持つ。

2.1 Tier 1: Working Memory（短期記憶）
実体: プロンプト内の会話コンテキスト。
用途: 現在のタスクの試行錯誤（Attempt History）。

2.2 Tier 2: Core Knowledge（永続ルール）
実体: workspace/.ark_memory/core_rules.json
用途: プロジェクトの「絶対の掟」。毎回の PLANNING 時に Goal へ自動注入される。
例: 「コメントには💋を付ける」「Tailwind CSSを優先する」。

2.3 Tier 3: Episodic Archive（エピソード記憶）
実体: chroma_db (Vector DB)
用途: 過去の成功体験、エラーの解決策。
アクセス: recall_memory ツールによる自律的な引き出し。

3. SYLPH Roles（エージェントの役割と義務）
3.1 Architect SYLPH
義務: ゴールを分析し、Tier 2 の掟と矛盾しないプランを立てる。
モデル: 思考力重視（例: gemma4:e4b）

3.2 Coder SYLPH
義務: 「職人」として最高品質のコードを書く。
品質基準: 全関数への型ヒント、docstring、PEP8準拠。
モデル: コーディング特化（例: qwen2.5-coder:7b）

3.3 Reviewer SYLPH
義務: 些細な型ミスの指摘よりも、「ユーザーの意図」と「コアルール（💋）」の遵守を最優先で評価する。
モデル: 判定速度重視（例: llama3.2:3b）

3.4 Reflector SYLPH (NEW! 🚀)
義務: ミッション完了後、今回の「成功」や「新ルール」を Tier 2/3 に記録する。
行動: save_core_rule または archive_experience の自律実行。

4. Communication Protocol
4.1 ReAct Interceptor（自律ツール実行）
モデルの Function Calling 能力に依存せず、テキストレスポンス内の特定のトリガーを Orchestrator が検知してツールを実行する。

フォーマット: TOOL_CALL: ツール名 | 引数1 | 引数2

Spec version: 0.2.0 — Authored by ARK Reflector — 2026-03-08