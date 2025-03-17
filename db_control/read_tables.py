from sqlalchemy import create_engine, text
import os
from pathlib import Path
from dotenv import load_dotenv

# 環境変数の読み込み
base_path = Path(__file__).parents[1]  # backendディレクトリへのパス
env_path = base_path / '.env'
load_dotenv(dotenv_path=env_path)

# データベース接続情報
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT', '3306')  # デフォルト値を設定
DB_NAME = os.getenv('DB_NAME')

# SSL証明書のパス
ssl_cert = str(base_path / 'DigiCertGlobalRootCA.crt.pem')

# MySQLのURL構築
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# エンジンの作成（SSL設定を追加）q
engine = create_engine(
    DATABASE_URL,
    connect_args={
        "ssl": {
            "ssl_ca": ssl_cert
        }
    },
    echo=True,
    pool_pre_ping=True,
    pool_recycle=3600
)

def print_table_info():
    with engine.connect() as connection:
        # テーブルの構造を取得
        print("\n=== customers テーブル情報 ===")
        columns = connection.execute(text("DESCRIBE customers"))  # textで囲む
        print("\nカラム情報:")
        print(f"{'フィールド名':<20} {'型':<15} {'Null':<6} {'キー':<5} {'デフォルト値':<15} {'その他'}")
        print("-" * 80)
        
        for column in columns:
            print(f"{column[0]:<20} {column[1]:<15} {column[2]:<6} {column[3]:<5} {str(column[4]):<15} {column[5]}")
        print("\n")

        # テーブルのデータを取得
        rows = connection.execute(text("SELECT * FROM customers"))  # textで囲む
        print("テーブルの内容:")
        print(f"{'id':<5} {'customer_id':<15} {'customer_name':<20} {'age':<5} {'gender':<6}")
        print("-" * 60)
        
        for row in rows:
            print(f"{row[0]:<5} {row[1]:<15} {row[2]:<20} {str(row[3]):<5} {row[4]:<6}")
        print("\n" + "="*50 + "\n")

# テーブル情報を表示
print_table_info()