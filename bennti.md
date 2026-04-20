【ベンチマークテスト: 認証機能付きToDo管理APIの構築】

# Goal
FastAPIとSQLiteを使用して、ユーザー認証（JWT）機能を備えたToDoタスク管理APIを構築してください。

# System Requirements
## 1. 概要
- 言語: Python 3.11+
- DB: SQLite (SQLAlchemy または SQLModel を使用)
- 認証: JWT (JSON Web Token) によるトークンベース認証

## 2. ディレクトリ構成（ARK標準モジュラー）
project_root/
├── main.py
├── api/ (ルーティング)
├── models/ (DBモデル・Pydanticスキーマ)
├── services/ (ビジネスロジック: 認証、DB操作)
└── core/ (設定管理: SECRET_KEY等)

## 3. 実装機能
- **ユーザー管理**: サインアップ、ログイン（JWT発行）
- **ToDo管理**: タスクの作成(C)、一覧取得(R)、更新(U)、削除(D)
  - ※各タスクは作成したユーザーに紐付けられ、他人のタスクは操作できないこと。

## 4. 制約事項
- `pydantic-settings` を使用して環境変数を管理すること。
- パスワードは必ずハッシュ化して保存すること。
- 各エンドポイントは適切にバリデーションを行い、エラー時は適切なHTTPステータスコードを返すこと。

# Execution
上記の要件を満たす、実際に動作可能な一連のソースコードを構築し、GitHubへPRを作成してください。