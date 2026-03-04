# ARK (Autonomous Resilient Kernel)
> **"Beyond the Cloud, Into the Sanctuary. Now, with the Will to Self-Evolve."**

ARKは、クラウドの干渉を排したローカル環境完結型の「自律型システム開発フレームワーク」です。
単なるコード生成を超え、**「自ら実行し、自らエラーを修復し、自ら歴史（Git）を刻む」**真の自律エージェントへと進化しました。

## 🌊 コンセプト
- **ARK (The Sanctuary)**: すべての思考とコードが完結する、安全で堅牢な開発拠点。
- **SYLPH (The Ethereal Agents)**: 
    - **Primary Intelligence**: Gemini 3 Flash / 2.5 Flash を主軸とした爆速の推論能力。
    - **Local Spirits**: プライバシーを重視したローカルLLM群（Gemma 3, DeepSeek等）との共生。

## 🧠 アーキテクチャ

### 1. 【脳】マルチモデル・オーケストレーション
タスクに応じて、ローカルモデルとSOTAモデルを動的にパッチ。
- **Context Awareness**: `read_file` ツールにより、プロジェクト全体の文脈を読み取る「視覚」を獲得。

### 2. 【脊髄】不滅の自律ループ (Resilient Loop)
- **Self-Healing**: 実行エラー（stderr）を解析し、原因を特定してコードを自動修正。
- **Short-Term Memory (Scratchpad)**: 試行錯誤の履歴を「短期メモリ」として保持。同じアプローチの失敗を繰り返さない学習ロジックを搭載。

### 3. 【意志】自律的バージョン管理 (Autonomous Git)
- **Automatic Branching**: タスクごとに専用のトピックブランチ（`ark/task-*`）を自動生成。
- **Smart Commit**: Conventional Commitsに準拠したメッセージをLLMが生成し、自らコミット＆プッシュを実行。

## 🚀 ロードマップ
- **Phase 1 (MVP)**: 基盤構築と仕様書自動生成。 [DONE]
- **Phase 2 (Incarnation)**: 自律修復ループとGit連携の完全受肉。 **[COMPLETED]** ✅
- **Phase 3 (Expansion)**: 
    - **Insight UI**: Streamlitによるリアルタイム思考プロセス可視化。
    - **Tool Use**: Web検索、パッケージ管理、外部API連携。
- **Phase 4 (Immortal)**: 長期メモリ（GraphRAG / Vector DB）によるプロジェクト全史の記憶。