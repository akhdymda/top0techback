import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import openai
from db_model.seed_data import seed_data, create_dummy_embedding
from db_connection.connect_Chroma import add_embedding, get_chroma_client
from db_connection.connect_MySQL import SessionLocal
from db_model.tables import SkillMaster, Profile, User

def init_chroma():
    """ChromaDBの初期化を行う"""
    try:
        print("ChromaDBの初期化を開始します...")
        
        # データベースの初期化
        print("データベースの初期化を実行します...")
        seed_data()
        
        # ChromaDBクライアントの初期化
        print("ChromaDBクライアントを初期化します...")
        client = get_chroma_client()
        
        # スキルマスタのエンベディング追加
        print("スキルマスタのエンベディングを追加します...")
        db = SessionLocal()
        try:
            skills = db.query(SkillMaster).all()
            print(f"スキルマスタのデータ数: {len(skills)}")
            
            for skill in skills:
                embedding = create_dummy_embedding(skill.name)
                metadata = {"skill_id": skill.skill_id, "name": skill.name}
                
                print(f"スキル '{skill.name}' (skill_id={skill.skill_id})のエンベディングを追加します")
                add_embedding(
                    id=f"skill_{skill.skill_id}",
                    embedding=embedding,
                    metadata=metadata,
                    text=skill.name,
                    collection_name="skills"
                )
            
            # プロフィールのエンベディング追加
            print("プロフィールのエンベディングを追加します...")
            profiles = db.query(Profile).join(User).all()
            print(f"プロフィールデータ数: {len(profiles)}")
            
            for profile in profiles:
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
            
            print("ChromaDBの初期化が完了しました")
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"ChromaDBの初期化中にエラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    init_chroma() 