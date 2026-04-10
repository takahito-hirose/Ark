# 環境変数とAPI設定 (API & Environment Variables)

システムを正しく起動・運用するためには、各種APIキーや認証トークンの設定が必要です。
本プロジェクト（`src/core/factory.py`、`src/api/slack_bot.py`、および `src/tools/telescope.py` などを基準）で要求される環境変数を以下にリストアップします。

## 必須・任意の設定項目

| 環境変数名 | 用途 | 必須度 |
| :--- | :--- | :--- |
| `SLACK_BOT_TOKEN` | Slack Botとしての発言やイベント取得に必要 (xoxb-...) | 必須（Slack連携時） |
| `SLACK_APP_TOKEN` | Slack Socket Modeでの常時接続に必要 (xapp-...) | 必須（Slack連携時） |
| `GEMINI_API_KEY` | Geminiモデル利用時のAPIキー | 任意（Gemini利用時必須） |
| `ANTHROPIC_API_KEY` | Claude系モデル利用時のAPIキー | 任意（Claude利用時必須） |
| `OPENAI_API_KEY` | GPT系モデル利用時のAPIキー | 任意（OpenAI利用時必須） |
| `DEEPSEEK_API_KEY` | DeepSeekモデル利用時のAPIキー | 任意（DeepSeek利用時必須） |
| `BRAVE_SEARCH_API_KEY` | Telescope（自律Web検索）機能を利用するためのAPIキー | 任意（Web検索機能利用時必須） |
| `OLLAMA_API_BASE` | OllamaのAPIエンドポイント（デフォルト: `http://localhost:11434`） | 任意 |

---

## `.env.example`

ルートディレクトリに配置すべき `.env` ファイルの雛形です。
> **※【プロジェクトの絶対制約事項】により、ドキュメントフォルダ（`.md`）以外へのファイル出力が禁止されているため、本ドキュメント内に雛形を記載しています。実際のプロジェクトルートに `.env.example` もしくは `.env` ファイルを手動で作成し、以下の内容をコピーして利用してください。**

```env
# Slack Integration
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_APP_TOKEN=xapp-your-slack-app-token

# LLM Provider API Keys
GEMINI_API_KEY=your-gemini-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
OPENAI_API_KEY=your-openai-api-key
DEEPSEEK_API_KEY=your-deepseek-api-key

# Web Search API
BRAVE_SEARCH_API_KEY=your-brave-search-api-key

# Optional: Local LLM Endpoint (Ollama)
# OLLAMA_API_BASE=http://localhost:11434
```

---

## 🔗 APIキーの主な取得先リンク

各種機能やクラウドモデルを利用する場合は、以下のダッシュボードからAPIキーを取得してください。

* **Brave Search API**: [https://brave.com/search/api/](https://brave.com/search/api/) （Freeプランで月2,000回まで無料）
* **Gemini (Google AI Studio)**: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
* **Anthropic (Claude)**: [https://console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)
* **OpenAI (GPT-4oなど)**: [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)

取得したキーは絶対に外部（GitHubの公開リポジトリなど）に漏れないよう、`.env` ファイルの管理には十分注意してください。