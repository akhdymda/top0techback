import os
import sys
from datetime import datetime, date
from pathlib import Path
import hashlib
import numpy as np
import openai
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL")

# 絶対パスを取得してpythonパスに追加
current_dir = Path(__file__).parent.absolute()  # db_modelディレクトリ
project_root = current_dir.parent  # プロジェクトルート
sys.path.insert(0, str(project_root))

try:
    from db_connection.connect_MySQL import SessionLocal, engine, Base
    from db_model.tables import (
        User, Department, JoinForm, WelcomeLevel, SkillMaster, 
        DetailSkill, ContactMethod, Profile, PostSkill, 
        PostContact, Thanks, Bookmark
    )
    from db_connection.connect_Chroma import add_embedding, get_chroma_client
except ModuleNotFoundError as e:
    print(f"モジュールのインポートエラー: {e}")
    print(f"現在のディレクトリ: {os.getcwd()}")
    print(f"Pythonパス: {sys.path}")
    sys.exit(1)

# 既存のテーブルをすべて削除して新しく作成
def drop_and_create_tables():
    try:
        print("既存のテーブルを削除して新しいテーブルを作成します...")
        # SQLAlchemyのtext関数を使ってSQLを実行
        with engine.begin() as conn:
            # 外部キー制約を一時的に無効化
            conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
            
            tables = [
                "bookmarks", "thanks", "post_contacts", "post_skills", 
                "profiles", "detail_skills", "contact_methods", "skill_masters", 
                "welcome_levels", "join_forms", "departments", "users"
            ]
            
            for table in tables:
                try:
                    conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
                    print(f"テーブル {table} を削除しました")
                except Exception as e:
                    print(f"テーブル {table} の削除中にエラー: {e}")
                    
            # 外部キー制約を有効化
            conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
        
        # SQLAlchemyのテーブル作成
        # 新しいテーブル構造にするため、SQLを直接使用
        with engine.begin() as conn:
            # ユーザーテーブル
            conn.execute(text("""
                CREATE TABLE users (
                    id INTEGER NOT NULL AUTO_INCREMENT, 
                    name VARCHAR(100), 
                    email VARCHAR(255) NOT NULL, 
                    password_hash VARCHAR(255) NOT NULL, 
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, 
                    PRIMARY KEY (id),
                    UNIQUE (email)
                )
            """))
            
            # 部署テーブル
            conn.execute(text("""
                CREATE TABLE departments (
                    id INTEGER NOT NULL AUTO_INCREMENT, 
                    name VARCHAR(100) NOT NULL, 
                    PRIMARY KEY (id)
                )
            """))
            
            # 入社形態テーブル
            conn.execute(text("""
                CREATE TABLE join_forms (
                    id INTEGER NOT NULL AUTO_INCREMENT, 
                    name VARCHAR(100) NOT NULL, 
                    PRIMARY KEY (id)
                )
            """))
            
            # 歓迎度テーブル
            conn.execute(text("""
                CREATE TABLE welcome_levels (
                    id INTEGER NOT NULL AUTO_INCREMENT, 
                    level_name VARCHAR(100) NOT NULL, 
                    PRIMARY KEY (id)
                )
            """))
            
            # スキルマスタテーブル
            conn.execute(text("""
                CREATE TABLE skill_masters (
                    skill_id INTEGER NOT NULL AUTO_INCREMENT, 
                    name VARCHAR(100) NOT NULL UNIQUE, 
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, 
                    PRIMARY KEY (skill_id)
                )
            """))
            
            # 連絡方法テーブル
            conn.execute(text("""
                CREATE TABLE contact_methods (
                    id INTEGER NOT NULL AUTO_INCREMENT, 
                    name VARCHAR(100) NOT NULL, 
                    PRIMARY KEY (id)
                )
            """))
            
            # 詳細スキルテーブル
            conn.execute(text("""
                CREATE TABLE detail_skills (
                    dskill_id INTEGER NOT NULL AUTO_INCREMENT, 
                    dskill_name VARCHAR(100) NOT NULL, 
                    skill_id INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, 
                    PRIMARY KEY (dskill_id), 
                    FOREIGN KEY(skill_id) REFERENCES skill_masters(skill_id) ON DELETE CASCADE
                )
            """))
            
            # プロフィールテーブル
            conn.execute(text("""
                CREATE TABLE profiles (
                    user_id INTEGER NOT NULL, 
                    department_id INTEGER, 
                    join_form_id INTEGER, 
                    welcome_level_id INTEGER, 
                    career INTEGER, 
                    image_url VARCHAR(255), 
                    history TEXT, 
                    pr TEXT, 
                    total_point INTEGER DEFAULT 0, 
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, 
                    PRIMARY KEY (user_id), 
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY(department_id) REFERENCES departments(id),
                    FOREIGN KEY(join_form_id) REFERENCES join_forms(id),
                    FOREIGN KEY(welcome_level_id) REFERENCES welcome_levels(id)
                )
            """))
            
            # ユーザースキルテーブル
            conn.execute(text("""
                CREATE TABLE post_skills (
                    id INTEGER NOT NULL AUTO_INCREMENT, 
                    user_id INTEGER NOT NULL, 
                    skill_id INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, 
                    PRIMARY KEY (id), 
                    UNIQUE KEY unique_user_skill (user_id, skill_id),
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY(skill_id) REFERENCES skill_masters(skill_id) ON DELETE CASCADE
                )
            """))
            
            # ユーザー連絡先テーブル
            conn.execute(text("""
                CREATE TABLE post_contacts (
                    id INTEGER NOT NULL AUTO_INCREMENT, 
                    user_id INTEGER NOT NULL, 
                    contact_id INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,  
                    PRIMARY KEY (id), 
                    UNIQUE KEY unique_user_contact (user_id, contact_id),
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY(contact_id) REFERENCES contact_methods(id) ON DELETE CASCADE
                )
            """))
            
            # サンクスポイントテーブル
            conn.execute(text("""
                CREATE TABLE thanks (
                    id INTEGER NOT NULL AUTO_INCREMENT, 
                    give_date DATE NOT NULL, 
                    giver_user_id INTEGER NOT NULL, 
                    receiver_user_id INTEGER NOT NULL, 
                    points INTEGER NOT NULL DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
                    PRIMARY KEY (id), 
                    FOREIGN KEY(giver_user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY(receiver_user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """))
            
            # ブックマークテーブル
            conn.execute(text("""
                CREATE TABLE bookmarks (
                    id INTEGER NOT NULL AUTO_INCREMENT, 
                    bookmark_date DATE NOT NULL, 
                    bookmarking_user_id INTEGER NOT NULL, 
                    bookmarked_user_id INTEGER NOT NULL, 
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
                    PRIMARY KEY (id), 
                    UNIQUE KEY unique_bookmark (bookmarking_user_id, bookmarked_user_id),
                    FOREIGN KEY(bookmarking_user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY(bookmarked_user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """))
        
        print("SQL直接実行によるテーブル作成完了")
        return True
    except Exception as e:
        print(f"テーブル作成中にエラーが発生しました: {e}")
        return False

# パスワードハッシュ化のヘルパー関数
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ダミーエンベディングを生成（実際には適切なエンベディングモデルを使用すべき）
def create_dummy_embedding(text, dimension=384):
    # OpenAIのエンベディングモデルを使用
    try:
        print(f"テキスト '{text}' のエンベディングを生成中...")
        response = openai.embeddings.create(
            model=OPENAI_MODEL,
            input=text
        )
        embedding = response.data[0].embedding
        print(f"エンベディング生成完了: 次元数={len(embedding)}")
        return embedding
    except Exception as e:
        print(f"エンベディング生成エラー: {str(e)}")
        # 失敗した場合はランダムなエンベディングを生成（デバッグ用）
        random_embedding = np.random.normal(0, 1, dimension).tolist()
        print(f"代わりにランダムエンベディングを生成: 次元数={len(random_embedding)}")
        return random_embedding

def seed_data():
    # まず新しいテーブル構造を作成
    if not drop_and_create_tables():
        return

    db = SessionLocal()
    try:
        # 部署データ
        departments = [
            Department(name="企画部"),
            Department(name="リビング戦略部"),
            Department(name="リビング営業部"),
            Department(name="エネルギー事業革新部"),
            Department(name="リビング業務改革部"),
            Department(name="設備ソリューション事業部"),
            Department(name="総合設備事業部"),
            Department(name="BTMソリューションプロジェクト部"),
            Department(name="WEBソリューションプロジェクト部"),
            Department(name="ソリューション共創本部")
        ]
        db.add_all(departments)
        db.commit()
        
        # 入社形態データ
        join_forms = [
            JoinForm(name="新卒入社"),
            JoinForm(name="中途入社"),
            JoinForm(name="派遣社員"),
            JoinForm(name="契約社員"),
            JoinForm(name="アルバイト")
        ]
        db.add_all(join_forms)
        db.commit()
        
        # 歓迎度データ
        welcome_levels = [
            WelcomeLevel(level_name="いつでも相談歓迎"),
            WelcomeLevel(level_name="相談歓迎"),
            WelcomeLevel(level_name="今は対応不可")
        ]
        db.add_all(welcome_levels)
        db.commit()
        
        # スキルマスタデータ
        skill_masters = [
            SkillMaster(name="WEBマーケティング全般"),
            SkillMaster(name="SEO（検索エンジン最適化）"),
            SkillMaster(name="コンテンツマーケティング"),
            SkillMaster(name="SNSマーケティング"),
            SkillMaster(name="広告運用（PPC・リスティング）"),
            SkillMaster(name="メールマーケティング"),
            SkillMaster(name="マーケティングオートメーション（MA）"),
            SkillMaster(name="データ分析と計測"),
            SkillMaster(name="グロースハック"),
            SkillMaster(name="Eコマース・D2Cマーケティング"),
            SkillMaster(name="AI・最新テクノロジーの活用")
        ]
        db.add_all(skill_masters)
        db.commit()
        
        # 詳細スキルデータ
        detail_skills = [
            DetailSkill(dskill_name="WEBマーケティングの基本領域と手法", skill_id=1),
            DetailSkill(dskill_name="KPI設定と効果測定", skill_id=1),
            DetailSkill(dskill_name="内部SEO対策", skill_id=2),
            DetailSkill(dskill_name="コアウェブバイタル", skill_id=2),
            DetailSkill(dskill_name="コンテンツ設計", skill_id=3),
            DetailSkill(dskill_name="コンテンツ戦略", skill_id=3),
            DetailSkill(dskill_name="SNSキャンペーン設計", skill_id=4),
            DetailSkill(dskill_name="SNSプラットフォーム選定", skill_id=4),
            DetailSkill(dskill_name="キーワード戦略・広告クリエイティブ", skill_id=5),
            DetailSkill(dskill_name="広告パフォーマンス", skill_id=5),
            DetailSkill(dskill_name="セグメント別パーソナライズ戦略", skill_id=6),
            DetailSkill(dskill_name="ステップメール", skill_id=6),
            DetailSkill(dskill_name="リード管理・育成", skill_id=7),
            DetailSkill(dskill_name="顧客スコアリング", skill_id=7),
            DetailSkill(dskill_name="Pythonによるデータ分析", skill_id=8),
            DetailSkill(dskill_name="統計的手法の活用", skill_id=8),
            DetailSkill(dskill_name="AARRRモデル", skill_id=9),
            DetailSkill(dskill_name="仮説検証サイクル", skill_id=9),
            DetailSkill(dskill_name="SNSとインフルエンサー活用", skill_id=10),
            DetailSkill(dskill_name="ライブコマースと広告の戦略的活用", skill_id=10),
            DetailSkill(dskill_name="自然言語処理・画像認識技術", skill_id=11),
            DetailSkill(dskill_name="AI導入", skill_id=11)   
        ]
        db.add_all(detail_skills)
        db.commit()
        
        # 連絡方法データ
        contact_methods = [
            ContactMethod(name="メール"),
            ContactMethod(name="Slack"),
            ContactMethod(name="Teams"),
            ContactMethod(name="対面"),
            ContactMethod(name="電話")
        ]
        db.add_all(contact_methods)
        db.commit()
        
        # ユーザーデータ
        users = [
            User(name="山田太郎", email="yamada@example.com", password_hash=hash_password("password123")),
            User(name="佐藤花子", email="sato@example.com", password_hash=hash_password("password133")),
            User(name="鈴木一郎", email="suzuki@example.com", password_hash=hash_password("password223")),
            User(name="高橋次郎", email="takahashi@example.com", password_hash=hash_password("password323")),
            User(name="田中三郎", email="tanaka@example.com", password_hash=hash_password("password423")),
            User(name="佐藤健", email="sato@example.com", password_hash=hash_password("password123")),
            User(name="鈴木大輔", email="suzuki@example.com", password_hash=hash_password("password123")),
            User(name="高橋翔太", email="takahashi@example.com", password_hash=hash_password("password123")),
            User(name="田中優子", email="tanaka@example.com", password_hash=hash_password("password123")),
            User(name="伊藤真理", email="ito@example.com", password_hash=hash_password("password123")),
            User(name="渡辺直人", email="watanabe@example.com", password_hash=hash_password("password123")),
            User(name="山本彩", email="yamamoto@example.com", password_hash=hash_password("password123")),
            User(name="中村光", email="nakamura@example.com", password_hash=hash_password("password123")),
            User(name="小林誠", email="kobayashi@example.com", password_hash=hash_password("password123")),
            User(name="加藤愛", email="kato@example.com", password_hash=hash_password("password123")),
            User(name="吉田和也", email="yoshida@example.com", password_hash=hash_password("password123")),
            User(name="山田花子", email="hanako@example.com", password_hash=hash_password("password123")),
            User(name="佐々木亮", email="ryo@example.com", password_hash=hash_password("password123")),
            User(name="山口萌", email="moe@example.com", password_hash=hash_password("password123")),
            User(name="松本健一", email="kenichi@example.com", password_hash=hash_password("password123")),
            User(name="井上美咲", email="misaki@example.com", password_hash=hash_password("password123")),
            User(name="木村拓哉", email="takuya@example.com", password_hash=hash_password("password123")),
            User(name="林美優", email="miyu@example.com", password_hash=hash_password("password123")),
            User(name="斎藤学", email="manabu@example.com", password_hash=hash_password("password123")),
            User(name="清水彩", email="aya@example.com", password_hash=hash_password("password123")),
            User(name="森田涼介", email="ryosuke@example.com", password_hash=hash_password("password123")),
            User(name="藤井直美", email="naomi@example.com", password_hash=hash_password("password123")),
            User(name="岡田真一", email="shinichi@example.com", password_hash=hash_password("password123")),
            User(name="中島美香", email="mika@example.com", password_hash=hash_password("password123")),
            User(name="石井陽子", email="yoko@example.com", password_hash=hash_password("password123"))
        ]
        db.add_all(users)
        db.commit()
        
        # プロフィールデータ
        profiles = [
            Profile(user_id=1, department_id=1, join_form_id=1, welcome_level_id=1, career=5, history="2018年入社", pr="Pythonが得意です", total_point=25),
            Profile(user_id=2, department_id=2, join_form_id=2, welcome_level_id=2, career=3, history="2020年入社", pr="営業経験豊富です", total_point=15 ),
            Profile(user_id=3, department_id=3, join_form_id=1, welcome_level_id=3, career=7, history="2016年入社", pr="人材採用を担当", total_point=30 ),
            Profile(user_id=4, department_id=4, join_form_id=3, welcome_level_id=3, career=2, history="2021年入社", pr="会計資格保持", total_point=10 ),
            Profile(user_id=5, department_id=5, join_form_id=1, welcome_level_id=1, career=4, history="2019年入社", pr="プロジェクト企画が得意", total_point=20 ),
            Profile(user_id=6, department_id=6, join_form_id=2, welcome_level_id=1, career=6, history="2017年入社", pr="デザインが得意です", total_point=18 ),
            Profile(user_id=7, department_id=7, join_form_id=3, welcome_level_id=2, career=4, history="2019年入社", pr="プロジェクトマネジメント経験豊富", total_point=22 ),
            Profile(user_id=8, department_id=8, join_form_id=1, welcome_level_id=3, career=5, history="2018年入社", pr="データ分析が専門です",  total_point=19 ),
            Profile(user_id=9, department_id=9, join_form_id=2, welcome_level_id=1, career=3, history="2020年入社", pr="マーケティング戦略立案が得意", total_point=17 ),
            Profile(user_id=10, department_id=10, join_form_id=3, welcome_level_id=2, career=7, history="2016年入社", pr="システム開発の経験があります", total_point=25),
            Profile(user_id=11, department_id=1, join_form_id=1, welcome_level_id=1, career=2, history="2021年入社", pr="SNS運用が得意です", total_point=12),
            Profile(user_id=12, department_id=2, join_form_id=2, welcome_level_id=3, career=8, history="2015年入社", pr="営業マネジメント経験があります", total_point=30),
            Profile(user_id=13, department_id=3, join_form_id=3, welcome_level_id=2, career=6, history="2017年入社", pr="コンテンツ制作が専門です", total_point=20),
            Profile(user_id=14, department_id=4, join_form_id=1, welcome_level_id=1, career=4, history="2019年入社", pr="広告運用のスペシャリストです", total_point=18),
            Profile(user_id=15, department_id=5, join_form_id=2, welcome_level_id=3, career=5, history="2018年入社", pr="SEO対策が得意です", total_point=22),
            Profile(user_id=16, department_id=6, join_form_id=3, welcome_level_id=2, career=3, history="2020年入社", pr="動画編集の経験があります", total_point=15),
            Profile(user_id=17, department_id=7, join_form_id=1, welcome_level_id=1, career=7, history="2016年入社", pr="ブランディング戦略が専門です", total_point=28),
            Profile(user_id=18, department_id=8, join_form_id=2, welcome_level_id=3, career=4, history="2019年入社", pr="イベント企画が得意です", total_point=19),
            Profile(user_id=19, department_id=9, join_form_id=3, welcome_level_id=2, career=5, history="2018年入社", pr="PR活動の経験があります", total_point=21),
            Profile(user_id=20, department_id=10, join_form_id=1, welcome_level_id=1, career=6, history="2017年入社", pr="市場調査が専門です", total_point=23),
            Profile(user_id=21, department_id=1, join_form_id=2, welcome_level_id=2, career=5, history="2018年入社", pr="メールマーケティングが得意", total_point=19),
            Profile(user_id=22, department_id=2, join_form_id=3, welcome_level_id=1, career=6, history="2017年入社", pr="UXリサーチ経験あり", total_point=24),
            Profile(user_id=23, department_id=3, join_form_id=1, welcome_level_id=3, career=2, history="2021年入社", pr="AI導入プロジェクトを担当", total_point=16),
            Profile(user_id=24, department_id=4, join_form_id=2, welcome_level_id=1, career=7, history="2016年入社", pr="統計解析が得意", total_point=27),
            Profile(user_id=25, department_id=5, join_form_id=3, welcome_level_id=2, career=3, history="2020年入社", pr="SEOコンテンツの制作実績多数", total_point=18),
            Profile(user_id=26, department_id=6, join_form_id=1, welcome_level_id=2, career=4, history="2019年入社", pr="D2Cブランドの立ち上げ経験あり", total_point=22),
            Profile(user_id=27, department_id=7, join_form_id=2, welcome_level_id=3, career=5, history="2018年入社", pr="インフルエンサーマーケ経験あり", total_point=20),
            Profile(user_id=28, department_id=8, join_form_id=3, welcome_level_id=1, career=6, history="2017年入社", pr="Pythonでのデータ分析が得意", total_point=26),
            Profile(user_id=29, department_id=9, join_form_id=1, welcome_level_id=2, career=2, history="2021年入社", pr="コンテンツ企画に自信あり", total_point=14),
            Profile(user_id=30, department_id=10, join_form_id=2, welcome_level_id=3, career=7, history="2016年入社", pr="広告クリエイティブの設計者", total_point=30),
        ]
        db.add_all(profiles)
        db.commit()
        
        # ユーザースキルデータ
        post_skills = [
            # 山田のスキル
            PostSkill(user_id=1, skill_id=1),
            PostSkill(user_id=1, skill_id=3),
            PostSkill(user_id=1, skill_id=5),
            PostSkill(user_id=1, skill_id=11),
            PostSkill(user_id=1, skill_id=4),
            # 佐藤のスキル
            PostSkill(user_id=2, skill_id=4),
            PostSkill(user_id=2, skill_id=3),
            PostSkill(user_id=2, skill_id=6),
            PostSkill(user_id=2, skill_id=2),
            # 鈴木のスキル
            PostSkill(user_id=3, skill_id=3),
            PostSkill(user_id=3, skill_id=4),
            PostSkill(user_id=3, skill_id=5),
            PostSkill(user_id=3, skill_id=6),
            PostSkill(user_id=3, skill_id=8),
            # 高橋のスキル
            PostSkill(user_id=4, skill_id=5),
            PostSkill(user_id=4, skill_id=3),
            PostSkill(user_id=4, skill_id=7),
            # 田中のスキル
            PostSkill(user_id=5, skill_id=2),
            PostSkill(user_id=5, skill_id=3),
            PostSkill(user_id=5, skill_id=5),
            PostSkill(user_id=5, skill_id=8),
            PostSkill(user_id=5, skill_id=9),

            # user 6
            PostSkill(user_id=6, skill_id=1),
            PostSkill(user_id=6, skill_id=2),
            PostSkill(user_id=6, skill_id=3),
            # user 7
            PostSkill(user_id=7, skill_id=2),
            PostSkill(user_id=7, skill_id=3),
            PostSkill(user_id=7, skill_id=4),
            # user 8
            PostSkill(user_id=8, skill_id=3),
            PostSkill(user_id=8, skill_id=4),
            PostSkill(user_id=8, skill_id=5),
            # user 9
            PostSkill(user_id=9, skill_id=4),
            PostSkill(user_id=9, skill_id=5),
            PostSkill(user_id=9, skill_id=6),
            # user 10
            PostSkill(user_id=10, skill_id=5),
            PostSkill(user_id=10, skill_id=6),
            PostSkill(user_id=10, skill_id=7),
            # user 11
            PostSkill(user_id=11, skill_id=6),
            PostSkill(user_id=11, skill_id=7),
            PostSkill(user_id=11, skill_id=8),
            # user 12
            PostSkill(user_id=12, skill_id=7),
            PostSkill(user_id=12, skill_id=8),
            PostSkill(user_id=12, skill_id=9),
            # user 13
            PostSkill(user_id=13, skill_id=8),
            PostSkill(user_id=13, skill_id=9),
            PostSkill(user_id=13, skill_id=10),
            # user 14
            PostSkill(user_id=14, skill_id=9),
            PostSkill(user_id=14, skill_id=10),
            PostSkill(user_id=14, skill_id=11),
            # user 15
            PostSkill(user_id=15, skill_id=10),
            PostSkill(user_id=15, skill_id=11),
            PostSkill(user_id=15, skill_id=1),
            # user 16
            PostSkill(user_id=16, skill_id=11),
            PostSkill(user_id=16, skill_id=1),
            PostSkill(user_id=16, skill_id=2),
            # user 17
            PostSkill(user_id=17, skill_id=1),
            PostSkill(user_id=17, skill_id=2),
            PostSkill(user_id=17, skill_id=3),
            # user 18
            PostSkill(user_id=18, skill_id=2),
            PostSkill(user_id=18, skill_id=3),
            PostSkill(user_id=18, skill_id=4),
            # user 19
            PostSkill(user_id=19, skill_id=3),
            PostSkill(user_id=19, skill_id=4),
            PostSkill(user_id=19, skill_id=5),
            # user 20
            PostSkill(user_id=20, skill_id=4),
            PostSkill(user_id=20, skill_id=5),
            PostSkill(user_id=20, skill_id=6),
            # user 21
            PostSkill(user_id=21, skill_id=5),
            PostSkill(user_id=21, skill_id=6),
            PostSkill(user_id=21, skill_id=7),
            # user 22
            PostSkill(user_id=22, skill_id=6),
            PostSkill(user_id=22, skill_id=7),
            PostSkill(user_id=22, skill_id=8),
            # user 23
            PostSkill(user_id=23, skill_id=7),
            PostSkill(user_id=23, skill_id=8),
            PostSkill(user_id=23, skill_id=9),
            # user 24
            PostSkill(user_id=24, skill_id=8),
            PostSkill(user_id=24, skill_id=9),
            PostSkill(user_id=24, skill_id=10),
            # user 25
            PostSkill(user_id=25, skill_id=9),
            PostSkill(user_id=25, skill_id=10),
            PostSkill(user_id=25, skill_id=11),
            # user 26
            PostSkill(user_id=26, skill_id=10),
            PostSkill(user_id=26, skill_id=11),
            PostSkill(user_id=26, skill_id=1),
            # user 27
            PostSkill(user_id=27, skill_id=11),
            PostSkill(user_id=27, skill_id=1),
            PostSkill(user_id=27, skill_id=2),
            # user 28
            PostSkill(user_id=28, skill_id=1),
            PostSkill(user_id=28, skill_id=2),
            PostSkill(user_id=28, skill_id=3),
            # user 29
            PostSkill(user_id=29, skill_id=2),
            PostSkill(user_id=29, skill_id=3),
            PostSkill(user_id=29, skill_id=4),
            # user 30
            PostSkill(user_id=30, skill_id=3),
            PostSkill(user_id=30, skill_id=4),
            PostSkill(user_id=30, skill_id=5)
        ]
        db.add_all(post_skills)
        db.commit()
        
        # ユーザー連絡先データ
        post_contacts = [
            PostContact(user_id=1, contact_id=1),  # 山田：メール
            PostContact(user_id=1, contact_id=2),  # 山田：Slack
            PostContact(user_id=2, contact_id=3),  # 佐藤：Teams
            PostContact(user_id=3, contact_id=4),  # 鈴木：対面
            PostContact(user_id=4, contact_id=5),  # 高橋：電話
            PostContact(user_id=5, contact_id=2)   # 田中：Slack
        ]
        db.add_all(post_contacts)
        db.commit()
        
        # サンクスポイントデータ
        thanks_points = [
            Thanks(give_date=date(2023, 5, 15), giver_user_id=1, receiver_user_id=2, points=3),
            Thanks(give_date=date(2023, 5, 16), giver_user_id=2, receiver_user_id=3, points=2),
            Thanks(give_date=date(2023, 5, 17), giver_user_id=3, receiver_user_id=4, points=1),
            Thanks(give_date=date(2023, 5, 18), giver_user_id=4, receiver_user_id=5, points=2),
            Thanks(give_date=date(2023, 5, 19), giver_user_id=5, receiver_user_id=1, points=3)
        ]
        db.add_all(thanks_points)
        db.commit()
        
        # ブックマークデータ
        bookmarks = [
            Bookmark(bookmark_date=date(2023, 6, 1), bookmarking_user_id=1, bookmarked_user_id=2),
            Bookmark(bookmark_date=date(2023, 6, 2), bookmarking_user_id=2, bookmarked_user_id=3),
            Bookmark(bookmark_date=date(2023, 6, 3), bookmarking_user_id=3, bookmarked_user_id=4),
            Bookmark(bookmark_date=date(2023, 6, 4), bookmarking_user_id=4, bookmarked_user_id=5),
            Bookmark(bookmark_date=date(2023, 6, 5), bookmarking_user_id=5, bookmarked_user_id=1)
        ]
        db.add_all(bookmarks)
        db.commit()
        
        # SkillMasterデータとユーザースキルデータをChromaDBにも追加
        print("\nChromaDBにスキルとプロフィールのエンベディングを追加します...")
        
        # スキルマスタのエンベディング追加
        skills = db.query(SkillMaster).all()
        print(f"スキルマスタのデータ数: {len(skills)}")
        for skill in skills:
            # 実際のアプリケーションでは適切なエンベディングモデルを使用
            embedding = create_dummy_embedding(skill.name)
            metadata = {"skill_id": skill.skill_id, "name": skill.name}
            
            print(f"スキル '{skill.name}' (skill_id={skill.skill_id})のエンベディングを追加します")
            
            # エンベディングの追加
            add_embedding(
                id=f"skill_{skill.skill_id}",  # 'skill_N'形式でIDを設定する
                embedding=embedding,
                metadata=metadata,
                text=skill.name,
                collection_name="skills"
            )
        
        # ユーザープロフィールのエンベディング追加
        profiles = db.query(Profile).join(User).all()
        print(f"プロフィールデータ数: {len(profiles)}")
        for profile in profiles:
            # プロフィールの特徴を表すテキスト作成
            profile_text = f"{profile.user.name} {profile.pr} {profile.history}"
            embedding = create_dummy_embedding(profile_text)
            metadata = {
                "user_id": profile.user_id,
                "name": profile.user.name,
                "department_id": profile.department_id,
                "career": profile.career
            }
            
            print(f"プロフィール '{profile.user.name}' (user_id={profile.user_id})のエンベディングを追加します")
            add_embedding(
                id=f"profile_{profile.user_id}",
                embedding=embedding,
                metadata=metadata,
                text=profile_text,
                collection_name="profiles"
            )
        
        print("データシードが完了しました")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data() 