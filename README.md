# 🚢 ARK (Autonomous Resilient Kernel)

> "クラウドの洪水から逃れ、独立した聖域へ。自律と進化の『方舟』、起動。"

ARKは、クラウドの干渉や制限を排した、ローカル環境完結型の**「自律型システム開発フレームワーク」**です。
単なるコード生成ツールを超え、「自ら針路を決め、自ら環境を整備し、自ら嵐（エラー）を乗り越え、自ら外界の知識を獲得し、自ら経験を記憶し、自ら航海日誌（Git）を刻む」、真の自律エージェント船へと進化しました。

---

## 🌊 コンセプト：方舟 (The Ark)

* **The Sanctuary (堅牢な船体):** すべての思考とコードがローカルで完結する、安全で独立した開発拠点。
* **SYLPH (風の精霊たち):** 方舟を動かす不可視のエージェント群。
    * **Main Mast:** Gemini 2.5 Flash 等を主軸とした爆速の推論能力。
    * **Local Sails:** プライバシーを完全に守るローカルLLM群（Gemma 3, Qwen 2.5 Coder, Llama 3.2 等）によるオフライン航海。

---

## ⚙️ 船体構造（アーキテクチャ）

### 1. 【操舵室】マルチモデル・ナビゲーション (Bridge)
海域（タスク）に応じて、ローカルモデルと最新SOTAモデルを動的に切り替え。
* **Context Radar:** `read_file` ツールにより、プロジェクト全体の文脈を読み取る「視覚と海図」を獲得。

### 2. 【機関室】不滅の自律制御ループ (Engine Room)
* **Auto-Bailing (自動修復):** 実行エラー（浸水）を解析し、原因を特定してコードを自動修正。どんな嵐でも方舟は沈みません。
* **Short-Term Log (短期記憶):** 試行錯誤の履歴を一時メモリとして保持。同じ座礁（失敗）を繰り返さず、常に前へ進みます。

### 3. 【大図書館】3層階層化・長期記憶システム (The Archives) 🧠
* **Core Knowledge (掟):** `core_rules.json` によるプロジェクト独自の絶対ルールの永続化。
* **Episodic Archive (経験):** Vector DB (ChromaDB) を用いた、過去の成功体験やエラー解決策のベクトル検索基盤。
* **Reflector SYLPH:** 航海完了後に「振り返り」を行い、自律的に知見を抽出して記憶ツールを実行する専用エージェント。

### 4. 【甲板作業】ターミナル・クレーン (Deck Operations)
* **Autonomous Setup:** `requirements.txt` を自動検知し、自ら `pip install` を実行。方舟の必要資材は自ら調達・構築します。
* **Command Execution:** 生成したコードを実際のOS環境で実行・検証し、その結果を操舵室へフィードバック。

### 5. 【望遠鏡】外界知識の自律獲得 (The Web Telescope) 🔭
* **Brave Search API:** 最新のドキュメントや技術スタックを調査するため、自律的にWeb検索とスクレイピングを実行し、プロンプトに知識を統合します。

### 6. 【造船所】プロジェクト・ドック (The Dock) 🏗️
* **Isolated Docking:** メインワークスペースから隔離された、タスクごとの独立したプロジェクトフォルダを自動生成。
* **GitHub Automatic Deployment:** GitHub APIを利用し、自律的にリモートリポジトリを新規作成・射出。母艦（ARK）から新しい「探査船」が次々と旅立ちます。

### 7. 【ニューロ・リンク】APIサーバー ＆ リアルタイム通信 (Neuro-Link) 🔌
* **FastAPI Core:** 外部システムやUIからの命令をREST API経由で受け付ける「感覚神経」を実装。
* **WebSocket Streaming:** ARKの思考プロセス（脳波）をリアルタイムに配信。ブラウザ上のダッシュボードへ直接思考ログを流し込みます。

---

## 🚀 航海ロードマップ

- [x] **Phase 1 (進水式):** 基盤構築と仕様書自動生成。
- [x] **Phase 2 (自律航行):** 自動修復ループとGit連携の完全実装。
- [x] **Phase 3 (外洋進出):** ターミナル操作と自動環境構築の統合。
- [x] **Phase 4 (深淵の叡智):**
    - **Knowledge Search:** Web検索（Brave Search）による最新知識の自律獲得。
    - **Long-term Memory:** プロジェクト全史を記憶する階層化メモリとReflectorによる自律学習。
- [x] **Phase 4.5 (プロジェクト・ドック):**
    - **GitHub Token API:** リモートリポジトリの自動生成とプロジェクトの隔離管理の実装。
    - **Neuro-Link:** APIサーバー化とWebSocketによるストリーミング基盤の構築。
- [x] **Phase 5 (The Grand Voyage - Neuro-Link UI):**
    - **Dynamic Insight UI:** React / Tailwind / Three.js を用いた、リアルタイムな思考・航路の超没入型可視化（操舵室UI）。
    - **The Synapse:** フロントエンドとバックエンドの完全非同期結合。
- [ ] **Phase 6 (The Treasury & Beyond): 🚀 NEXT**
    - **Token Economy:** 実際のエージェント推論に基づくリアルタイムなトークン（金貨）消費計算の実装。
    - **Autonomous Collaboration:** 複数のARKプロジェクト間でのコード共有と自動連携。

---

## ⚓️ 起動シークエンス (How to Run ARK)

ARKの操舵室（UI）と機関室（バックエンド）を完全に同期させるための起動手順です。ターミナルを2つ開いて実行してください。

### 1. 機関室（バックエンド）の起動

プロジェクトのルートディレクトリ（`ARK_ROOT`）で、FastAPIサーバーを立ち上げます。
※ `workspace` での自律コーディングによる無限再起動を防ぐため、監視対象を `src` のみに絞っています。

```bash
# プロジェクトルートで実行
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir src