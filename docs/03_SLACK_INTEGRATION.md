# Slack連携アーキテクチャと設定手順 (Slack Integration)

ARKは、外界（ユーザー）からの指示を受け取るためのインターフェースとしてSlackを利用します（`src/api/slack_bot.py` で実装されています）。

## アーキテクチャの概要

本システムでは、**Slack Socket Mode** を利用して通信を行っています。
- **セキュリティ・ネットワークの安全性**: Socket Modeを利用することで、外部からアクセス可能なエンドポイント（Public URLやWebhook）を公開する必要がなくなり、ファイアウォール内部から安全にSlackとリアルタイム通信（WebSocket）を行うことができます。
- **インタラクティブなUI連携**: メンションでのコマンド受付、プロバイダー（使用モデル）の動的選択を行うドロップダウン、ミッション承認・却下のボタンなどをSlackのBlock Kitを用いて実装し、高度なインタラクションを提供しています。

## Slack Developer Dashboard でのセットアップ手順（チュートリアル）

Slackと連携させるためには、Slack Developer Dashboardでアプリを作成し、必要なトークンを発行・取得する必要があります。

### 1. アプリの作成
1. [Slack API: Applications](https://api.slack.com/apps) にアクセスし、「**Create New App**」をクリックします。
2. 「From scratch」を選択し、任意のアプリ名（例: `ARK-System`）と対象のワークスペースを選択して作成します。

### 2. App-Level Tokenの取得（Socket Mode用）
1. 左側メニューの「**Basic Information**」を選び、画面を下へスクロールして「**App-Level Tokens**」セクションへ行きます。
2. 「**Generate Token and Scopes**」をクリックします。
3. トークン名を入力し、スコープ（権限）として `connections:write` を追加して生成します。
4. 生成された `xapp-...` で始まるトークンをコピーします。これが環境変数 `SLACK_APP_TOKEN` になります。

### 3. Socket Modeの有効化
1. 左側メニューから「**Socket Mode**」を選択します。
2. 「Enable Socket Mode」のスイッチを **On** に切り替えます。

### 4. Bot Tokenの取得と権限設定
1. 左側メニューから「**OAuth & Permissions**」を選択します。
2. 画面を下へスクロールし、「Scopes」 > 「Bot Token Scopes」に進みます。
3. 「Add an OAuth Scope」をクリックし、以下の権限を追加します。
   - `app_mentions:read` (Botへのメンションを読み取るため)
   - `chat:write` (チャンネルにメッセージを送信するため)
4. 画面上部の「**Install to Workspace**」ボタンをクリックし、ワークスペースにアプリをインストールします。
5. インストール完了後、同じ画面の「OAuth Tokens for Your Workspace」セクションに `xoxb-...` で始まるトークンが表示されます。これが環境変数 `SLACK_BOT_TOKEN` になります。

### 5. Event Subscriptionsの設定（イベントの購読）
1. 左側メニューから「**Event Subscriptions**」を選択します。
2. 「Enable Events」のスイッチを **On** にします（Socket Modeが有効になっているため、Request URLの入力は不要です）。
3. 「Subscribe to bot events」セクションを開き、「Add Bot User Event」から `app_mention` を追加します。
4. 画面下部の「**Save Changes**」をクリックして設定を保存します。

以上でSlack Developer側の設定は完了です。取得した2つのトークン（`xoxb-...` と `xapp-...`）を `.env` ファイルに設定してシステムを起動してください。

### 6. チャンネルへのBot追加と動作確認
ワークスペースへのインストールが完了しても、そのままではチャンネル内でBotを呼び出すことはできません。

1. Slackを開き、ARKを稼働させたいチャンネル（例: `#ark-ops` など）に移動します。
2. メッセージ入力欄で `@ARK-System` （手順1で設定したアプリ名）とメンションを入力して送信します。
3. 「このアプリはチャンネルに参加していません」という通知が出るので、「**チャンネルに追加する**」をクリックします。
4. ARKのバックエンド（`uvicorn src.api.main:app ...`）が起動している状態で、`@ARK-System こんにちは` とメンションし、モデル選択のUIが返ってくれば接続成功です！