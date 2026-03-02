# ARK (Autonomous Resilient Kernel)
> **"Beyond the Cloud, Into the Sanctuary."**

ARKは、クラウドという外界の嵐（プライバシーリスク、外的干渉、不安定なAPI）から切り離された、ローカル環境完結型の「自律型システム開発フレームワーク」です。開発者は一人の「観測者」として、この聖域の中で知性が自己進化する様を指揮します。

## 🌊 コンセプト
- **ARK (The Sanctuary)**: 物理マシン内に構築された堅牢な開発拠点。すべての思考プロセスとコードは、この「箱舟」の外には漏れません。
- **SYLPH (The Ethereal Agents)**: ARKの帆に受ける風。軽量・爆速なローカルLLMを駆使し、設計・実装・検証をミリ秒単位でループさせる自律精霊（エージェント）たちの総称。

## 🧠 アーキテクチャ（4大要素）

### 1. 【脳】マルチモデル・オーケストレーション
タスクの特性に応じて最適なローカルモデルを動的にパッチ。
- **Architect**: 論理構造の定義（DeepSeek-V3 / Llama-3.1-70B）
- **Coder**: 実装と文法（Qwen2.5-Coder / Gemma-2-9B）
- **Reviewer**: 高速な監査とテスト（Llama-3.2-3B / Phi-4）

### 2. 【脊髄】自律駆動ワークフロー (Autonomous Loop)
- **State Management**: フェーズごとの状態遷移を管理。
- **Circuit Breaker**: 無限ループを検知し、安全に停止・介入。
- **Sandbox**: 実行検証はDocker隔離環境で行い、ホストOSを保護。

### 3. 【記憶】コンテキスト・マネジメント
- **Spec-driven Development**: 実装前のMarkdown仕様書を共有記憶とする。
- **GraphRAG**: コードの関係性を抽象構文木(AST)でパースし、依存関係を知識グラフ化。

### 4. 【視覚】Insight UI
- **Real-time Log**: エージェント間の秘めやかな対話を可視化。
- **Mermaid Graph**: システム構成図と依存関係の自動生成。

## 🚀 ロードマップ
- **Phase 1 (MVP)**: Architectによるディレクトリ構造と仕様書の自動生成。
- **Phase 2 (Loop)**: CoderとReviewerによる「実装→検証」の完全自律ループ。
- **Phase 3 (Insight)**: 生成プロセスの可視化ダッシュボード。