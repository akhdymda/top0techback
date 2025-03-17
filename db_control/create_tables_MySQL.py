import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, text
from sqlalchemy.orm import declarative_base, sessionmaker

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

# エンジンの作成（SSL設定を追加）
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

# Baseクラスの作成
Base = declarative_base()

# テーブルの定義
class Customer(Base):
   __tablename__ = 'customers'

   id = Column(Integer, primary_key=True, autoincrement=True)
   customer_id = Column(String(50), unique=True, nullable=False)
   customer_name = Column(String(100), nullable=False)
   age = Column(Integer)
   gender = Column(String(10))

   def __repr__(self):
       return f"<Customer(customer_id='{self.customer_id}', name='{self.customer_name}')>"

# テーブルの作成
Base.metadata.create_all(engine)

# セッションの作成
Session = sessionmaker(bind=engine)
session = Session()

def add_test_data():
   # 既存のデータを削除
   with engine.connect() as connection:
       connection.execute(text("DELETE FROM customers"))
       connection.commit()
   
   test_customers = [
       Customer(customer_id='C1111', customer_name='ああ', age=6, gender='男'),
       Customer(customer_id='C110', customer_name='桃太郎', age=30, gender='女')
   ]
   
   for customer in test_customers:
       session.add(customer)
   
   try:
       session.commit()
       print("テストデータを追加しました")
   except Exception as e:
       session.rollback()
       print(f"エラーが発生しました: {e}")
   finally:
       session.close()

# この行を追加
if __name__ == "__main__":
    add_test_data()  # テストデータの追加を実行