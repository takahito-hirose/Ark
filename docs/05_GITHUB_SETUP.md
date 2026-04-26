# GitHub連携セットアップ手順 (GitHub Setup Guide)

ARKは、開発したソースコードを自動的にGitHubへアップロードし、プルリクエストを作成する機能を備えています。
さらに、コードの品質を担保する「絶対防衛網（The Pharos）」をGitHub Actionsとして全プロジェクトへ自動配備します。

この機能を有効にするためには、GitHubのパーソナルアクセストークン（PAT）と、GitHub CLI（`gh`）のセットアップが必要です。

---

## 🏗️ GitHub連携の概要

なぜこのシステムに `GITHUB_TOKEN` や `gh` CLI が必要なのか、その主な用途は以下の通りです：

1.  **新規リポジトリの自動建造**:
    新しいプロジェクトを開始する際、GitHub上にリモートリポジトリを自動的に作成します。
2.  **認証プロンプトのバイパス**:
    トークンをURLに埋め込むことで、パスワード入力などの対話型認証をバイパスし、安全かつスムーズな自動Pushを実現します。
3.  **PR（Pull Request）の自動作成**:
    変更内容をPushした後、ブラウザで即座に確認・マージできるよう、PRの比較ページURLを自動生成します。
4.  **絶対防衛網（The Pharos）の自動配備**:
    ARKが触れたすべてのリポジトリに対し、自動で `.github/workflows/pharos-audit.yml` を生成し、監査に必要なAPIキーを `gh` コマンド経由でGitHub Secretsに自動注入します。

これらは `src/core/git_tools.py` および `src/core/github_publisher.py` のロジックによって制御されています。

---

## 🔑 1. Personal Access Token (PAT) 取得手順

GitHubのAPIを操作するためのトークンを取得します。

1.  GitHubにログインし、右上のアイコンから **Settings** を開きます。
2.  左サイドメニューの一番下にある **<> Developer settings** をクリックします。
3.  **Personal access tokens** > **Tokens (classic)** を選択します。
4.  **Generate new token** ボタンを押し、**Generate new token (classic)** を選択します。
5.  **Note** に「ARK-Integration」など、用途がわかる名前を入力します。
6.  **【最重要】スコープ（権限）の設定**: 以下の2つに必ずチェックを入れてください。
    * ✅ **`repo`** (Full control of private repositories) : リポジトリの作成やPushに必要です。
    * ✅ **`workflow`** (Update GitHub Action workflows) : The PharosのYAMLファイル(`.github/workflows/...`)を自動コミット・Pushするために必須です。
7.  一番下の **Generate token** をクリックします。
8.  表示されたトークン（`ghp_...` で始まる文字列）をコピーします。
    * **※一度ページを離れると二度と表示されないため、必ず控えをとってください。**

### ⚙️ 環境変数への設定

コピーしたトークンを、プロジェクトルートの `.env` ファイルに設定します。

```env
GITHUB_TOKEN=ghp_YourCopiedTokenContext...
```

---

## 🐙 2. GitHub CLI (`gh`) のインストールと認証

The Pharosがクラウド上で動くための鍵（APIキー）を、各リポジトリの「GitHub Secrets」に自動登録するために `gh` コマンドを使用します。

### Mac の場合
ターミナルを開き、Homebrewを使ってインストールします。
```bash
brew install gh
```

### 認証セットアップ
インストール後、以下のコマンドを実行してGitHubアカウントを認証させます。
```bash
gh auth login
```
画面の指示に従って、以下の通りに進めてください。
1. *What account do you want to log into?* -> **GitHub.com**
2. *What is your preferred protocol for Git operations?* -> **HTTPS**
3. *Authenticate Git with your GitHub credentials?* -> **Yes**
4. *How would you like to authenticate GitHub CLI?* -> **Login with a web browser**
（ブラウザが開き、ワンタイムコードを入力して承認すれば完了です）

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