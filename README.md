# 🚢 ARK (Autonomous Resilient Kernel)

> "クラウドの洪水から逃れ、独立した聖域へ。自律と進化の『方舟』、起動。"

ARKは、クラウドの干渉や制限を排した、ローカル環境完結型の**「自律型システム開発フレームワーク」**です。
単なるコード生成ツールを超え、「自ら針路を決め、自ら環境を整備し、自ら嵐（エラー）を乗り越え、自ら外界の知識を獲得し、自ら経験を記憶し、自ら航海日誌（Git）を刻む」、真の自律エージェント船へと進化しました。

## 🥊 既存AIツールとの決定的な違い（なぜARKを選ぶのか？）

ClineやCursorといった既存のツールが「高性能な磁針や櫂（ツール）」であるなら、ARKは**「伝説の航海士と熟練の船員が乗り込み、目的地を告げるだけで荒波を越える自動航行ガレオン船」**です。

* **💥 「道具」ではなく「自律した船団」**: 既存ツールは人間が漕がなければ進みませんが、ARKは **Fire and Forget（撃ちっ放し）**。目的地を告げてコーヒーを飲んでいる間に、ブランチの作成、環境構築、テスト、エラーの自己修復、GitHubへのPull Request作成までを自律的に完遂します。
* **📚 航海を重ねるほど賢くなる「大図書館」**: 過去の座礁（エラー）や発見（成功体験）をベクトルDBに蓄積。使えば使うほど、そのプロジェクト特有の海図（暗黙知）を覚え、専用の最強航海士へと成長します。
* **🔭 霧を晴らす「自律望遠鏡」**: 訓練データにない最新の海域（ライブラリ）に直面しても、自律的にWebを捜索。最新のドキュメントを読み込み、未知の技術スタックをその場で習得して航行を続けます。
* **🪙 航海予算を管理する「金庫番」**: 穏やかな海域（単純作業）では低コストなローカルLLMを、難所（複雑な改修）では最高峰のクラウドLLMを動的に切り替え。品質と金貨（トークン）の消費を最適化します。

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
* **GitHub Automatic Deployment:** 成功が確定した瞬間にのみリポジトリを作成・射出する「遅延射出プロトコル（Lazy Creation）」により、クリーンな航海を実現します。

### 7. 【ニューロ・リンク】APIサーバー ＆ リアルタイム通信 (Neuro-Link) 🔌
* **FastAPI Core:** 外部システムやUIからの命令をREST API経由で受け付ける「感覚神経」を実装。
* **WebSocket Streaming:** ARKの思考プロセス（脳波）をリアルタイムに配信。ブラウザ上のダッシュボードへ直接思考ログを流し込みます。

### 8. 【金庫】トークン・エコノミー (The Treasury) 🪙
ARKが消費したLLMの推論コスト（トークン数）をリアルタイムに計算し、操舵室（UI）の金貨メーターに反映するシステムです。
* **Token Calculation:** バックエンドの各エージェントが推論を行うたびに、プロバイダーから正確な消費トークン数を取得します（Ollama等のAPIから取得できない場合は、`(プロンプト文字数 + 生成文字数) / 4` の計算式で高精度な概算を算出します）。
* **Real-time Sync:** 計算されたトークン消費量は、WebSocket経由（`TOKEN_USAGE` イベント）で瞬時にフロントエンドのHUDへ送信されます。
* **Cost Estimation:** フロントエンドのストア（Zustand）にて、現在の市場相場（例: 100,000トークン = $1.00 等）を基にリアルタイムなコスト計算を行い、エージェントが思考するたびにチャリンと金貨を消費する様子を可視化します。

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
- [x] **Phase 6 (The Treasury):**
    - **Token Economy:** 実際のエージェント推論に基づくリアルタイムなトークン（金貨）消費計算とWebSocket連携の実装。
- [x] **Phase 7 (The Grand Fleet & UI Evolution):**
    - **GitHub Auto-Deploy Fix:** GitHub APIのリポジトリ作成・権限エラーを解消し、探査船（リモートリポジトリ）の完全自律射出を修復。
    - **Model Selector (Eco / Rich):** 操舵室（HUD）に切り替えスイッチを実装。ローカルLLMでコストを抑える「Ecoモード」と、API経由でSOTAモデル（Gemini等）をフル稼働させる「Richモード」を動的に選択可能にする。
    - **HUD Expansion:** 要件定義書などの巨大なテキストを直接ペーストできるよう、ミッション入力コンソールのUI領域を大容量化。
- [x] **Phase 8 (The Deep Sea Trials):**
    - **Stress Testing:** 複雑で大規模な要件定義を実際に投入し、Architectのタスク分割能力、Coderの実装力、そしてシステム全体のエラー修復耐性（Auto-Bailing）を検証する耐久テスト航海。
- [ ] **Phase 9 (The Continuous Voyage - 1→100 Evolution): 🚀 NOW**
    - [x] **Existing Repo Ingestion:** 既存リポジトリをドックに読み込み、文脈を理解する機能。
    - [x] **Targeted Patching:** `SEARCH/REPLACE` による既存コードの精密修正能力。
    - [x] **Manual PR Link Generation:** Push完了後、ブラウザで即座にPRを作成できる比較URLの自動生成。
    - [ ] **Context Deep Dive:** AST（抽象構文木）解析による、より深いコード理解と大規模リファクタリングへの対応。- [ ] **Phase 10 (The Deep Archives & Horizon - 堅牢化と限界突破):** 🌟 **NEW!**
    - **Telescope Calibration (望遠鏡のテスト):** 訓練データに含まれていない最新・超マイナーなライブラリを使用した無茶振りミッションを投下し、望遠鏡（Brave Search）の自律リサーチ＆解決能力を実地検証・強化する。
    - **Memory Garbage Collection (大図書館の整理整頓):** 長期稼働に伴って蓄積されたルールや経験のストレステストと大掃除。重複・矛盾するルールの自律的なパージ機能の実装と、ChromaDBの検索精度（コサイン類似度）の極限チューニング。
- [ ] **Phase 11 (The Universal Port - MCP Integration):** 🌐 **VISION!**
    - **Model Context Protocol (MCP):** MCPを「万能接続ポート」として採用。ターミナルやGit操作だけでなく、Slack通知やデータベース操作、外部ドキュメント検索など、世界中の標準化されたツール（外部機器）をプラグイン感覚で自律的に使いこなす「超・汎用型ガレオン船」への進化。

> **MISSION STATUS: PHASE 8 COMPLETE. ALL SYSTEMS SECURED. ⚓️**

---

## ⚓️ 起動シークエンス (How to Run ARK)

ARKの操舵室（UI）と機関室（バックエンド）を完全に同期させるための起動手順です。ターミナルを2つ開いて実行してください。

### 1. 機関室（バックエンド）の起動

プロジェクトのルートディレクトリ（`ARK_ROOT`）で、FastAPIサーバーを立ち上げます。
※ `workspace` での自律コーディングによる無限再起動を防ぐため、監視対象を `src` のみに絞っています。

```bash
# プロジェクトルートで実行
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir src
```

### 2. 操舵室（フロントエンドHUD）の起動

次に、Next.jsで構築されたホログラムUIを立ち上げます。

```bash
# ark-odissey フォルダに移動して実行
cd ark-odissey
npm run dev
```

### 3. ニューロ・リンク接続

ブラウザで `http://localhost:3000` にアクセスします。
右下のターミナル（SYLPH ACTIVITY）に `[SYSTEM]: Neuro-Link (WebSocket) Connection Established. 🧠✨` と表示されれば、ARKとの神経接続は完了です。コマンドを入力して、自律航行を開始してください！