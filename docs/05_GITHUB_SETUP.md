# GitHub連携セットアップ手順 (GitHub Setup Guide)

ARKは、開発したソースコードを自動的にGitHubへアップロードし、プルリクエストを作成する機能を備えています。
この機能を有効にするためには、GitHubのパーソナルアクセストークン（PAT）の設定が必要です。

---

## 🏗️ GitHub連携の概要

なぜこのシステムに `GITHUB_TOKEN` が必要なのか、その主な用途は以下の通りです：

1.  **新規リポジトリの自動建造**:
    新しいプロジェクトを開始する際、GitHub上にリモートリポジトリを自動的に作成します。
2.  **認証プロンプトのバイパス**:
    トークンをURLに埋め込むことで、パスワード入力などの対話型認証をバイパスし、安全かつスムーズな自動Pushを実現します。
3.  **PR（Pull Request）の自動作成**:
    変更内容をPushした後、ブラウザで即座に確認・マージできるよう、PRの比較ページURLを自動生成します。

これらは `src/core/git_tools.py` および `src/core/github_publisher.py` のロジックによって制御されています。

---

## 🔑 Personal Access Token (PAT) 取得手順

GitHubのAPIを操作するためのトークンを取得します。

1.  GitHubにログインし、右上のアイコンから **Settings** を開きます。
2.  左サイドメニューの一番下にある **<> Developer settings** をクリックします。
3.  **Personal access tokens** > **Tokens (classic)** を選択します。
4.  **Generate new token** ボタンを押し、**Generate new token (classic)** を選択します。
5.  **Note** に「ARK-Integration」など、用途がわかる名前を入力します。
6.  **【最重要】スコープ（権限）の設定**:
    *   **`repo`** (Full control of private repositories) のチェックボックスに必ずチェックを入れてください。
    *   これがないと、リポジトリの作成やPushができません。
7.  一番下の **Generate token** をクリックします。
8.  表示されたトークン（`ghp_...` で始まる文字列）をコピーします。
    *   **※一度ページを離れると二度と表示されないため、必ず控えをとってください。**

### ⚙️ 環境変数への設定

コピーしたトークンを、プロジェクトルートの `.env` ファイルに設定します。

```env
GITHUB_TOKEN=ghp_YourCopiedTokenContext...
```

---

## ✒️ Gitのコミット署名（オプション）

ARKはデフォルトで **「ARK SYLPH <sylph@ark.local>」** という名前でコミット履歴を生成します。
これを自分の名前に変更したい場合は、`.env` に以下の変数を追加してください。

```env
# 自分の名前とメールアドレスに設定可能
GIT_AUTHOR_NAME="Your Name"
GIT_AUTHOR_EMAIL="your-email@example.com"
```

設定しない場合は、ARKのデフォルトアイデンティティが使用されます。
