# 環境構築ガイド (Setup Guide)

ARKプロジェクトに参画される皆様、ようこそ。
本ドキュメントでは、本システムをローカルで稼働させるための前提環境とセットアップ手順を解説します。

## 前提環境

以下の実行環境がインストールされていることを確認してください。

- **Python**: 3.11以上（バックエンドの主要言語です）
- **Node.js**: 18以上推奨（HUDとなるReactフロントエンドの実行に必要です）
- **Git**: （ARKが自律的にブランチ作成やPRを行うために必要です）

## ローカルLLM (Ollama) のセットアップ

ARKの思考・コード生成エンジンとして、プライバシーが保護されたローカルLLMの利用が可能です。
推奨エンジンとして `Ollama` を使用します。

### インストール手順

1. [Ollama 公式サイト](https://ollama.com/)から、OS環境に合わせたインストーラーをダウンロードし、インストールします。
2. ターミナルを開き、推奨モデル（`qwen2.5-coder:7b`など）をダウンロードします。
   ```bash
   ollama run qwen2.5-coder:7b
   ```

### 注意事項：Ollamaの起動方法について（CORSエラー回避）

HUD（Reactフロントエンド）からローカルのOllama APIに直接アクセスする際、ブラウザのセキュリティ制限によりCORS（Cross-Origin Resource Sharing）エラーが発生する場合があります。
これを防ぐため、**デスクトップアプリのアイコンから起動するのではなく、ターミナルから以下のコマンドで起動**してください。

**■ Mac / Linux / Git Bash の場合**
```bash
OLLAMA_ORIGINS="*" ollama serve
```

**■ Windows (PowerShell) の場合**
```powershell
$env:OLLAMA_ORIGINS="*"; ollama serve
```

**■ Windows (コマンドプロンプト) の場合**
```cmd
set OLLAMA_ORIGINS="*" && ollama serve
```

これにより、HUDからのアクセスが許可され、正常にARKのシステムと連携されるようになります。

## プロジェクトの依存パッケージのインストール

Ollamaの準備ができたら、ARK本体のパッケージをインストールします。

**1. バックエンド（Python）の準備**
プロジェクトのルートディレクトリで以下のコマンドを実行します。
```bash
pip install -r requirements.txt
```

**2. フロントエンド（Node.js）の準備**
UI用のディレクトリに移動してパッケージをインストールします。
```bash
cd ark-odissey
npm install
```