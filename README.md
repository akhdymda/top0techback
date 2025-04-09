# LinkFastNect Backend API

スキル検索システムのバックエンドAPI

## 環境構築

1. 必要なパッケージのインストール:
```bash
pip install -r requirements.txt
```

2. `.env`ファイルの設定:
```
DB_USER = "ユーザー名"
DB_PASSWORD = "パスワード"
DB_HOST = "ホスト名"
DB_PORT = "3306"
DB_NAME = "データベース名"

PINECONE_API_KEY = "Pinecone APIキー"
PINECONE_ENVIRONMENT = "gcp-starter"
PINECONE_INDEX_NAME = "skills-index"

OPENAI_API_KEY = "OpenAI APIキー"
OPENAI_MODEL = "text-embedding-ada-002"
```

3. データベースのセットアップとPineconeへのデータ登録:
```bash
python load_pinecone_data.py
```

4. アプリケーションの起動:
```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

## 主な機能

- `/skills` - スキル一覧を取得
- `/skills/{skill_name}` - 特定のスキルとそれを持つユーザーを取得
- `/departments` - 部署一覧を取得
- `/departments/{department_name}` - 特定の部署とそのユーザーを取得
- `/search?query=XXX&limit=N` - ベクトル検索でスキルやユーザーを検索
- `/user/{user_id}` - 特定のユーザー情報を取得

## ユーティリティスクリプト

- `load_pinecone_data.py` - データベースからPineconeにスキルデータを登録
- `check_pinecone.py` - Pineconeのデータ状態を確認（デバッグ用）

## 技術スタック

- FastAPI - Webフレームワーク
- SQLAlchemy - ORMマッパー
- Pinecone - ベクトルデータベース
- OpenAI - テキスト埋め込み生成

## 環境変数備忘
SCM_DO_BUILD_DURING_DEPLOYMENT:1
