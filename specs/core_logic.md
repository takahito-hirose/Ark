# ARK Core Logic Specification
> **Spec-driven Development** — このドキュメントはARK Orchestratorの「設計書」であり、  
> すべてのSYLPHエージェントの実装はこの仕様に準拠しなければならない。

---

## 1. Autonomous Loop（自律駆動ループ）

ARKの心臓部は **Plan → Code → Review → Commit** の4フェーズからなる  
閉ループ（Autonomous Loop）として設計される。

```
┌─────────────────────────────────────────────────────────────┐
│                          USER GOAL                          │
└──────────────────────────────┬──────────────────────────────┘
                               │ Task Payload (JSON)
                               ▼
                     ┌─────────────────┐
                     │  Orchestrator   │  ← State Machine
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
          FAIL×3   │ Breaker      │
                   └──────────────┘               │ FAIL (< 3)
                                                  ▼
                                         ┌─────────────────┐
                                         │  PHASE 2 (再試行) │
                                         │  Coder (retry)  │
                                         └─────────────────┘
```

### 1.1 フェーズ定義

| Phase | Agent | 入力 | 出力 | 終了条件 |
|-------|-------|------|------|----------|
| PLAN  | Architect | ユーザーゴール文字列 | `PlanPayload` | 仕様書（Markdown）の生成 |
| CODE  | Coder | `PlanPayload` | `CodePayload` | 対象ファイルの生成・変更 |
| REVIEW| Reviewer | `CodePayload` + テスト結果 | `ReviewPayload` | `status: PASS` または `FAIL` |
| COMMIT| Orchestrator | `ReviewPayload` | 最終成果物 | workspaceへのファイル書き込み |

### 1.2 State Machine（状態遷移）

```
IDLE → PLANNING → CODING → REVIEWING → COMMITTING → IDLE
                    ↑______________|
                    (FAIL: retry)
```

**状態はJSONファイル** (`workspace/.ark_state.json`) **で永続化する。**  
クラッシュ後も前回のフェーズから再開できること。

### 1.3 Circuit Breaker（安全停止）

- 同一タスクで `FAIL` が **3回連続** した場合、ループを強制停止。
- `workspace/.ark_state.json` の `retry_count` フィールドで追跡。
- 停止時は `status: BLOCKED` を設定し、ユーザーへの介入を要求する。

---

## 2. Communication Protocol（エージェント間通信）

すべてのSYLPH間通信は **JSON over stdout/stdin** または  
**Ollama REST API** (`/api/chat`) を介して行われる。

### 2.1 共通エンベロープ（Envelope）

```json
{
  "ark_version": "0.1.0",
  "task_id":     "uuid4文字列",
  "phase":       "PLAN | CODE | REVIEW | COMMIT",
  "timestamp":   "ISO 8601",
  "payload":     { /* フェーズ固有のオブジェクト */ },
  "metadata": {
    "model_name": "deepseek-coder-v2",
    "retry_count": 0
  }
}
```

### 2.2 PlanPayload（Architect → Coder）

```json
{
  "goal":         "ユーザーが与えたゴール文字列",
  "spec_path":    "specs/core_logic.md",
  "target_files": [
    "src/core/orchestrator.py"
  ],
  "constraints": [
    "Python 3.11+",
    "型ヒント必須",
    "既存ファイルを破壊しないこと"
  ],
  "acceptance_criteria": [
    "all tests pass",
    "no syntax errors"
  ]
}
```

### 2.3 CodePayload（Coder → Reviewer）

```json
{
  "plan_ref":    "task_idへの参照",
  "files": [
    {
      "path":    "src/core/orchestrator.py",
      "action":  "CREATE | MODIFY | DELETE",
      "content": "生成されたコード文字列"
    }
  ],
  "test_command": "pytest workspace/tests/ -v",
  "notes":        "実装メモ（任意）"
}
```

### 2.4 ReviewPayload（Reviewer → Orchestrator）

```json
{
  "status":   "PASS | FAIL",
  "score":    0.95,
  "issues": [
    {
      "severity": "ERROR | WARNING | INFO",
      "file":     "src/core/orchestrator.py",
      "line":     42,
      "message":  "未処理の例外パス"
    }
  ],
  "suggested_fix": "コードの修正案（FAIL時のみ）",
  "summary":       "レビュー結果の要約"
}
```

---

## 3. Agent Roles（精霊の役割定義）

### 3.1 Architect SYLPH

| 項目 | 詳細 |
|------|------|
| **ファイル** | `src/agents/architect.py` |
| **推奨モデル** | DeepSeek-V3 / Llama-3.1-70B |
| **責務** | ゴールを分析し、`PlanPayload` を生成する。specs/ に仕様書を書く |
| **プロンプト戦略** | System: 設計思想の注入 / User: ゴール文字列 |
| **出力形式** | `PlanPayload` JSON |
| **禁止事項** | コードを直接生成しないこと |

### 3.2 Coder SYLPH

| 項目 | 詳細 |
|------|------|
| **ファイル** | `src/agents/coder.py` |
| **推奨モデル** | Qwen2.5-Coder / Gemma-2-9B |
| **責務** | `PlanPayload` を受け取り、`workspace/` にコードを生成する |
| **プロンプト戦略** | System: コーディング規約 / User: PlanPayload JSON |
| **出力形式** | `CodePayload` JSON（生成コードを含む） |
| **禁止事項** | 仕様書を変更しないこと。`workspace/` 外への書き込み禁止 |

### 3.3 Reviewer SYLPH

| 項目 | 詳細 |
|------|------|
| **ファイル** | `src/agents/reviewer.py` |
| **推奨モデル** | Llama-3.2-3B / Phi-4 |
| **責務** | コードの品質・安全性を検証し `ReviewPayload` を返す |
| **プロンプト戦略** | System: コードレビュー観点の注入 / User: CodePayload JSON |
| **出力形式** | `ReviewPayload` JSON |
| **観点** | 型安全性 / セキュリティ / スペック適合性 / テスト通過 |

### 3.4 Orchestrator（非LLM）

| 項目 | 詳細 |
|------|------|
| **ファイル** | `src/core/orchestrator.py` |
| **責務** | ループ制御 / 状態管理 / Circuit Breaker / ファイル書き込み |
| **状態永続化** | `workspace/.ark_state.json` |
| **介入トリガー** | retry_count ≥ 3 |

---

## 4. 実装優先順位（Phase 1 MVP）

```
Priority 1:  src/core/orchestrator.py  ← ループと状態管理
Priority 2:  src/agents/architect.py   ← 最初のSYLPH
Priority 3:  src/agents/coder.py       ← コード生成エンジン
Priority 4:  src/agents/reviewer.py    ← 品質ゲート
Priority 5:  src/core/ollama_client.py ← Ollama REST APIラッパー
```

---

## 5. 将来的な拡張（Phase 2以降）

- **GraphRAG**: ASTパーサーによるコード依存関係のグラフ化 → `src/memory/graph_rag.py`
- **Docker Sandbox**: `workspace/` を隔離コンテナで実行 → セキュリティ強化
- **Insight UI**: エージェント間対話のリアルタイム可視化 → WebSocket + Mermaid

---

*Spec version: 0.1.0 — Authored by SYLPH Architect — 2026-03-02*
