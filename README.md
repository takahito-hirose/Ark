# 🚢 ARK (Autonomous Resilient Kernel)

> "クラウドの洪水から逃れ、独立した聖域へ。自律と進化の『方舟』、起動。"

ARKは、クラウドの干渉や制限を排した、ローカル環境完結型の**「自律型システム開発フレームワーク」**です。
単なるコード生成ツールを超え、「自ら針路を決め、自ら環境を整備し、自ら嵐（エラー）を乗り越え、自ら外界の知識を獲得し、自ら経験を記憶し、自ら航海日誌（Git）を刻む」、真の自律エージェント船へと進化しました。

## 🥊 既存AIツールとの決定的な違い（なぜARKを選ぶのか？）

ClineやCursorといった既存のツールが「高性能な磁針や櫂（ツール）」であるなら、ARKは**「伝説の航海士と熟練の船員が乗り込み、目的地を告げるだけで荒波を越える自動航行ガレオン船」**です。

* **💥 「道具」ではなく「自律した船団」**: 既存ツールは人間が漕がなければ進みませんが、ARKは **Fire and Forget（撃ちっ放し）**。目的地を告げてコーヒーを飲んでいる間に、ブランチの作成、環境構築、テスト、エラーの自己修復、GitHubへのPull Request作成までを自律的に完遂します。
* **📚 航海を重ねるほど賢くなる「大図書館」**: 成功体験だけでなく、**「なぜ座礁（エラー）したのか」**を徹底分析。致命的な失敗を「アンチパターン」として大図書館に蓄積し、次回の航海では最初からその罠を回避する、不屈の学習アルゴリズムを搭載しており使えば使うほどユーザー専用の最強航海士へと成長します。
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

### 3. 【大図書館】長期記憶・失敗分析システム (The Deep Archives) 🧠
* **Tiered Storage:** `core_rules.json`（絶対の掟）と `ChromaDB`（エピソード記憶）の2層構造。
* **Critical Failure Analysis:** 3回の試行でも解決できない致命的敗北に直面した際、死ぬ直前にReflector（司書）が全履歴を分析。二度と同じ轍を踏まないための「回避ルール（Avoidance Rules）」を作成し、知識ベースに刻み込みます。
* **Automatic RAG Injection:** ミッション開始時、Architectは大図書館から「過去の掟」と「地雷マップ」を自動で読み込み、最初から最適な航路（実装方針）を導き出します。
* **Reflector Librarian:** `/gc` コマンドにより、重複・矛盾する古い記憶を自律的に統合。脳内を常に最新・高精度な状態へ再構築（整理整頓）します。

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

## 🎮 指揮官コマンド (Command Deck)

操舵室（HUD）のコンソールから直接入力可能な特殊コマンド群です。

| コマンド | 役割 | 説明 |
| :--- | :--- | :--- |
| `/memory` | **記憶の閲覧** | 大図書館に蓄積された「コアルール」と「過去の経験（地雷マップ）」をすべて表示します。 |
| `/forget` | **忘却の執行** | 特定の不要になった記憶や誤った知見を、インデックス指定で大図書館から消去します。 |
| `/gc` | **記憶の整理整頓** | Reflectorを召喚し、乱雑になった記憶の重複を統合、矛盾をパージして脳内を再構築します。 |
| `/clear` | **ログの消去** | HUD上の思考ログ・表示をクリアします。 |

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
- [x] **Phase 9 (The Continuous Voyage - 1→100 Evolution):** 🚀 **COMPLETED**
    - [x] **Existing Repo Ingestion:** 既存リポジトリをドックに読み込み、文脈を理解する機能。
    - [x] **Targeted Patching:** `SEARCH/REPLACE` による既存コードの精密修正能力。
    - [x] **Manual PR Link Generation:** Push完了後、比較用URLの自動生成。
    - [x] **Resilient Parsing & Genesis Git:** 執念のパース能力とGit初期化エラーの撲滅。
- [ ] **Phase 10 (The Deep Archives & Horizon - 堅牢化と限界突破):** 🌟 **IN PROGRESS**
    - [x] **Telescope Calibration:** 未知のライブラリを用いた望遠鏡の自律リサーチ＆解決能力の検証。
    - [x] **Eco-Mock Protocol:** API消費を抑えつつ自律ループをテストするモック機能の実装。
    - [x] **Deep Memory Management:** 記憶へのメタデータ付与と、HUDからの `/memory`, `/forget` による手動管理機能。
    - [x] **Memory Garbage Collection:** 蓄積されたルールの矛盾パージと、Reflectorによる自律的な記憶の再構築（整理整頓）。
    - [x] **Failure Analytics:** 致命的な敗北から「地雷マップ」を生成する不屈の学習アルゴリズムの実装。
    - [x] **Auto RAG Injection:** 記憶を計画段階で自動注入し、過去の失敗を未然に防ぐ「予見能力」の獲得。
    - [x] **Memory Garbage Collection:** Reflectorによる自律的な記憶の再構築・整理整頓機能の実装。
    - [ ] **Similarity Threshold Tuning:** ChromaDBの検索精度（コサイン類似度）の極限チューニング。
- [x] **Phase 11 (The Universal Port & Seamless Voyage):** 🚀 **COMPLETED**
    - **Continue Mode:** ミッション完了後の次なる航路の自律提案機能。
    - **Branch Inheritance:** 同一プロジェクト内でのブランチ引き継ぎと、リポジトリの継続開発プロトコルの確立。
- [x] **Phase 12 (The Grand Fleet & TDD Pipeline):** 🚀 **COMPLETED**
    - [x] **The Grand Fleet (並列航行):** Coderのマルチスレッド化。Architectの指示に基づき分身エージェントを動的召喚し、フロントとバックエンド等を同時並行で実装。
    - [x] **Merge Protocol:** 複数スレッドによる衝突を防ぐ、排他制御（Lock機構）と直列マージキューの導入。
    - [x] **Immutable TDD Pipeline:** Architectがテストを先行生成し、Reviewerが機械的にテストを実行して冷酷に合否を判定する「絶対防衛テスト網」の構築。
- [x] **Phase 13 (ARK Remote Command):** 🚀 **COMPLETED**
    - [x] **Slack Bot（広報官）:** 外界からのプロンプトをキャッチし、SlackのBlock Kitを用いて承認や継続判断をインタラクティブに行う窓口の設置。
    - [x] **The Relay Server（次元の門）:** Socket Modeを採用し、ポート開放不要で自宅PCと外界を安全に繋ぐプル型通信の確立。
    - [x] **PR Notification Spy:** ターミナルログからPRのURLを自律検知し、Slackへ即座に任務完了報告を送信する監視網の実装。
- [x] **Phase 13.5 (Interactive Model Selection):** 🚀 **COMPLETED**
    - [x] **Dynamic Engine Fetcher:** 起動中のOllamaサーバーから利用可能なローカルモデル一覧をリアルタイムに取得。
    - [x] **UI/UX Sync:** SlackのドロップダウンUIと、HUD（React）のセレクトボックスに最新のモデルリストを完全同期。
    - [x] **Provider Routing:** `ollama|モデル名` や `gpt-4o` などの動的モデル指定を完璧に解釈し、APIをシームレスに切り替えるルーターの強化。
- [x] **Phase 14 (The Fleet Expansion - Onboarding & Documentation):** 🚀 **COMPLETED**
    - [x] **Setup Guide:** 前提環境とローカルLLM（Ollama）のCORS回避設定を含む初期構築手順の策定。
    - [x] **Environment Security:** `factory.py` 等から環境変数を抽出し、APIキーの取得先と雛形をまとめた設定ガイドの作成。
    - [x] **Slack Integration Guide:** Socket Modeのアーキテクチャ解説と、Bot作成・権限設定の完全チュートリアル構築。
    - [x] **Web Telescope Setup:** Brave Search APIの取得手順と、無料枠で稼働する安全設計（モックモード含む）の明文化。
    - [x] **GitHub Genesis Engine:** 自動リポジトリ生成・PushのためのPAT取得手順と、認証バイパスの仕組みのドキュメント化。

> **MISSION STATUS: PHASE 8 COMPLETE. ALL SYSTEMS SECURED. ⚓️**

---
## 🛠️ 事前準備 (Environment Setup)

ARKを初めて起動する際、または環境を最新に保つために、必要な資材（パッケージ）のインストールを行います。ß
特にナビゲーションの中核となる `litellm` は更新頻度が非常に高いため、定期的なアップグレードを推奨します。

### Windows環境の場合 (PowerShell / Command Prompt)

```powershell
# 1. 依存パッケージの一括インストール
python -m pip install -r requirements.txt

# ※ 特定のPythonパス（例: Python 3.11）を明示して実行する場合:
# C:\Users\[USER]\AppData\Local\Programs\Python\Python311\python.exe -m pip install -r requirements.txt

# 2. LiteLLMを最新版へアップグレード（推奨）
python -m pip install --upgrade litellm
```

### Mac / Linux環境の場合 (Terminal)
```powershell
# 1. 依存パッケージの一括インストール
python3 -m pip install -r requirements.txt

# 2. LiteLLMを最新版へアップグレード（推奨）
python3 -m pip install --upgrade litellm
```

## 🔰 新規参画者の方へ (Getting Started)

ARKの開発・運用に参加される方は、まず以下のドキュメントに沿って初期セットアップを完了させてください。

1. [環境構築ガイド](docs/01_SETUP_GUIDE.md) （Ollamaと前提環境の準備）
2. [環境変数とAPI設定](docs/02_API_AND_ENV.md) （必須APIキーの登録）
3. [Slack連携手順](docs/03_SLACK_INTEGRATION.md) （コマンド受付インターフェースの構築）
4. [Telescopeセットアップ](docs/04_TELESCOPE_SETUP.md) （自律Web検索機能の有効化）
5. [GitHubセットアップ](docs/05_GITHUB_SETUP.md) （リモートリポジトリ連携と自動Push機能の有効化）


## ⚓️ 起動シークエンス (How to Run ARK)

ARKの操舵室（UI）と機関室（バックエンド）を完全に同期させるための起動手順です。ターミナルを2つ開いて実行してください。

### 1. 機関室（バックエンド）の起動

プロジェクトのルートディレクトリ（`ARK_ROOT`）で、FastAPIサーバーを立ち上げます。
※ `workspace` での自律コーディングによる無限再起動を防ぐため、監視対象を `src` のみに絞っています。

```bash
# プロジェクトルートで実行
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir src
```

# サーバー起動（Python 3.11+）
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir src

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