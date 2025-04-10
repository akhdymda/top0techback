from db_connection.connect_MySQL import SessionLocal
from db_connection.connect_Pinecone import add_skill_to_pinecone
from db_model.tables import SkillMaster, PostSkill, User

def load_skills_to_pinecone():
    """データベースからスキルデータを取得してPineconeに格納"""
    print("スキルデータをPineconeに格納します...")
    
    # データベース接続
    db = SessionLocal()
    
    try:
        # 全てのスキルを取得
        all_skills = db.query(SkillMaster).all()
        print(f"データベースから{len(all_skills)}件のスキルデータを取得しました。")
        
        # Pineconeにスキルを格納
        for skill in all_skills:
            # スキル自体をPineconeに追加
            add_skill_to_pinecone(skill.skill_id, skill.name)
            
            # このスキルを持つユーザーを取得
            users_with_skill = (
                db.query(User)
                .join(PostSkill, User.id == PostSkill.user_id)
                .filter(PostSkill.skill_id == skill.skill_id)
                .all()
            )
            
            print(f"スキル '{skill.name}' を持つユーザー: {len(users_with_skill)}人")
            
            # ユーザーごとのスキル情報を追加
            for user in users_with_skill:
                add_skill_to_pinecone(
                    skill_id=skill.skill_id,
                    skill_name=skill.name,
                    user_id=user.id,
                    user_name=user.name or "名前なし"
                )
        
        print("スキルデータのPineconeへの格納が完了しました。")
    
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    load_skills_to_pinecone() 