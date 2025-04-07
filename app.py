from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from db_connection.connect_Chroma import list_collection_items, search_similar
from pydantic import BaseModel
from typing import List
from db_connection.connect_MySQL import SessionLocal, get_db
from db_model.tables import SkillMaster, User as DBUser, PostSkill, Department as DBDepartment, Profile
from sqlalchemy.orm import joinedload, Session
from db_model.schemas import SkillResponse, SearchResponse, UserResponse, SearchResult, DepartmentResponse
from db_connection.embedding import get_text_embedding

app = FastAPI()

# CORSミドルウェア設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では特定のオリジンに制限する
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# スキル検索API
@app.get("/skills/{skill_name}", response_model=SkillResponse)
def read_skill(skill_name: str):
    db = SessionLocal()
    try:
        # スキルを検索
        skill = db.query(SkillMaster).filter(SkillMaster.name == skill_name).first()
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")

        print(f"Found skill: {skill.name} (ID: {skill.skill_id})")

        # スキルを持つユーザーを取得
        users_with_skill = (
            db.query(DBUser)
            .join(PostSkill, DBUser.id == PostSkill.user_id)
            .join(Profile, DBUser.id == Profile.user_id)
            .join(DBDepartment, Profile.department_id == DBDepartment.id)
            .options(
                joinedload(DBUser.profile).joinedload(Profile.department),
                joinedload(DBUser.profile).joinedload(Profile.join_form),
                joinedload(DBUser.posted_skills).joinedload(PostSkill.skill)
            )
            .filter(PostSkill.skill_id == skill.skill_id)
            .order_by(DBUser.id)  # 一貫した順序で結果を取得
            .distinct()
            .all()
        )

        print(f"Found {len(users_with_skill)} users with skill")

        # レスポンス用のユーザーリストを作成
        users = []
        for user in users_with_skill:
            # ユーザーのスキルを取得
            user_skills = [ps.skill.name for ps in user.posted_skills]
            profile = user.profile
            
            # デバッグ情報を追加
            print(f"Processing user: {user.name} (ID: {user.id})")
            print(f"Department: {profile.department.name if profile and profile.department else '未所属'}")
            print(f"Join Form: {profile.join_form.name if profile and profile.join_form else '未設定'}")
            print(f"Skills: {user_skills}")

            users.append(
                UserResponse(
                    id=user.id,
                    name=user.name,
                    department=profile.department.name if profile and profile.department else "未所属",
                    yearsOfService=profile.career if profile else 0,
                    skills=user_skills,
                    description=profile.pr if profile else "",
                    joinForm=profile.join_form.name if profile and profile.join_form else "未設定"
                )
            )

        response = SkillResponse(name=skill_name, users=users)
        print(f"Sending response with {len(users)} users")
        return response

    finally:
        db.close()

# 全スキル取得API
@app.get("/skills", response_model=List[SkillResponse])
def read_skills():
    db = SessionLocal()
    try:
        skills = db.query(SkillMaster).all()
        
        skill_responses = []
        for skill in skills:
            # スキルを持つユーザーを取得
            users_with_skill = (
                db.query(DBUser)
                .join(PostSkill, DBUser.id == PostSkill.user_id)
                .join(SkillMaster, PostSkill.skill_id == SkillMaster.skill_id)
                .join(Profile, DBUser.id == Profile.user_id)
                .options(
                    joinedload(DBUser.profile).joinedload(Profile.department),
                    joinedload(DBUser.profile).joinedload(Profile.join_form),
                    joinedload(DBUser.posted_skills).joinedload(PostSkill.skill)
                )
                .filter(SkillMaster.name == skill.name)
                .all()
            )
            
            users = []
            for user in users_with_skill:
                # ユーザーのスキルを取得
                user_skills = []
                for post_skill in user.posted_skills:
                    print(f"Processing skill for user {user.name} in skill {skill.name}: {post_skill.skill.name}")
                    user_skills.append(post_skill.skill.name)

                profile = user.profile
                print(f"Processing user: {user.name} for skill {skill.name}")
                print(f"Skills: {user_skills}")
                
                users.append(
                    UserResponse(
                        id=user.id,
                        name=user.name,
                        department=profile.department.name if profile and profile.department else "未所属",
                        yearsOfService=profile.career if profile else 0,
                        skills=user_skills,
                        description=profile.pr if profile else "",
                        joinForm=profile.join_form.name if profile and profile.join_form else "未設定"
                    )
                )
            
            skill_responses.append(SkillResponse(name=skill.name, users=users))
        
        return skill_responses
    
    finally:
        db.close()


#ふわっと検索API
@app.get("/search", response_model=SearchResponse)
async def fuzzy_search(query: str, limit: int = 5, db: Session = Depends(get_db)):
    """
    ふわっと検索（ベクトル検索）でユーザーを検索
    """
    print(f"検索クエリ: {query}, 取得件数上限: {limit}")
    
    try:
        # テキストからエンベディングを生成
        embedding = get_text_embedding(query)
        print(f"エンベディング生成完了。次元数: {len(embedding)}")

        # ChromaDBで類似検索を実行
        results = search_similar(embedding, limit=limit)
        print(f"ChromaDB検索結果: {results}")

        # 検索結果がない場合
        if not results or not results.get("ids") or len(results["ids"][0]) == 0:
            print("検索結果なし")
            return SearchResponse(results=[], total=0)
        
        print(f"検索結果の件数: {len(results['ids'][0])}")
        
        # 結果をフォーマット
        search_results = []
        for i, id_str in enumerate(results["ids"][0]):
            print(f"処理中のID: {id_str}")
            
            # IDの形式を確認
            if id_str.startswith("skill_"):
                # skill_1 形式の場合は数字部分を抽出
                try:
                    skill_id = int(id_str.split("_")[1])
                    print(f"スキルIDに変換: {skill_id}")
                    
                    # スキルマスターからスキル情報を取得
                    skill = db.query(SkillMaster).filter(SkillMaster.skill_id == skill_id).first()
                    if not skill:
                        print(f"スキルID {skill_id} が見つかりません")
                        continue
                        
                    # スキルに関連付けられたポストスキルを全て取得
                    post_skills = db.query(PostSkill).filter(PostSkill.skill_id == skill_id).all()
                    if not post_skills:
                        print(f"スキルID {skill_id} に関連するポストスキルが見つかりません")
                        continue
                        
                    # 各ポストスキルからユーザー情報を取得して結果に追加
                    for post_skill in post_skills:
                        user = db.query(DBUser).filter(DBUser.id == post_skill.user_id).first()
                        if not user:
                            print(f"ユーザーID {post_skill.user_id} が見つかりません")
                            continue
                            
                        # 部署情報を取得
                        department_id = None
                        department_name = None
                        if user.profile and user.profile.department_id:
                            department = db.query(DBDepartment).filter(DBDepartment.id == user.profile.department_id).first()
                            if department:
                                department_id = department.id
                                department_name = department.name
                        
                        # 検索結果を作成
                        search_result = SearchResult(
                            user_id=user.id,
                            user_name=user.name or "名前なし",
                            skill_id=skill.skill_id,
                            skill_name=skill.name,
                            description=None,  # description フィールドは削除されましたが、スキーマとの整合性のために None を設定
                            department_id=department_id,
                            department_name=department_name,
                            similarity_score=results["distances"][0][i] if "distances" in results else 0.0
                        )
                        search_results.append(search_result)
                except Exception as e:
                    print(f"スキルID '{id_str}' の処理中にエラー: {str(e)}")
                    continue
            else:
                # 通常の数値IDとして処理を試みる
                try:
                    skill_id_int = int(id_str)
                    print(f"ポストスキルIDとして処理: {skill_id_int}")
                    
                    # データベースから投稿スキル情報を取得
                    post_skill = db.query(PostSkill).filter(PostSkill.id == skill_id_int).first()
                    if post_skill:
                        print(f"ポストスキル: user_id={post_skill.user_id}, skill_id={post_skill.skill_id}")
                        
                        # ユーザー情報を取得
                        user = db.query(DBUser).filter(DBUser.id == post_skill.user_id).first()
                        if not user:
                            print(f"ユーザーID {post_skill.user_id} が見つかりません")
                            continue

                        # スキル情報を取得
                        skill = db.query(SkillMaster).filter(SkillMaster.skill_id == post_skill.skill_id).first()
                        if not skill:
                            print(f"スキルID {post_skill.skill_id} が見つかりません")
                            continue

                        # 部署情報を取得
                        department_id = None
                        department_name = None
                        if user.profile and user.profile.department_id:
                            department = db.query(DBDepartment).filter(DBDepartment.id == user.profile.department_id).first()
                            if department:
                                department_id = department.id
                                department_name = department.name
                        
                        # 検索結果を作成
                        search_result = SearchResult(
                            user_id=user.id,
                            user_name=user.name or "名前なし",
                            skill_id=skill.skill_id,
                            skill_name=skill.name,
                            description=None,  # description フィールドは削除されましたが、スキーマとの整合性のために None を設定
                            department_id=department_id,
                            department_name=department_name,
                            similarity_score=results["distances"][0][i] if "distances" in results else 0.0
                        )
                        search_results.append(search_result)
                    else:
                        print(f"ID {id_str} に対応するポストスキルが見つかりません")
                except Exception as e:
                    print(f"ID '{id_str}' の処理中にエラー: {str(e)}")
                    continue
                
        print(f"整形後の検索結果: {len(search_results)}件")
        return SearchResponse(
            results = search_results,
            total = len(search_results))
    except Exception as e:
        print(f"検索処理中にエラーが発生: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"検索エラー: {str(e)}")

#部署検索API
@app.get("/departments/{department_name}", response_model=DepartmentResponse)
def read_department(department_name: str):
    db = SessionLocal()
    try:
        # 部署を検索
        department = db.query(DBDepartment).filter(DBDepartment.name == department_name).first()
        if not department:
            raise HTTPException(status_code=404, detail="Department not found")

        print(f"Found department: {department.name} (ID: {department.id})")

        # 部署に所属するユーザーを取得
        users_in_department = (
            db.query(DBUser)
            .join(Profile, DBUser.id == Profile.user_id)
            .join(DBDepartment, Profile.department_id == DBDepartment.id)
            .options(
                joinedload(DBUser.profile).joinedload(Profile.department),
                joinedload(DBUser.profile).joinedload(Profile.join_form),
                joinedload(DBUser.posted_skills).joinedload(PostSkill.skill)
            )
            .filter(DBDepartment.id == department.id)
            .order_by(DBUser.id)  # 一貫した順序で結果を取得
            .distinct()
            .all()
        )

        print(f"Found {len(users_in_department)} users in department")

        # レスポンス用のユーザーリストを作成
        users = []
        for user in users_in_department:
            # ユーザーのスキルを取得
            user_skills = [ps.skill.name for ps in user.posted_skills]
            profile = user.profile
            
            # デバッグ情報を追加
            print(f"Processing user: {user.name} (ID: {user.id})")
            print(f"Department: {department_name}")
            print(f"Join Form: {profile.join_form.name if profile and profile.join_form else '未設定'}")
            print(f"Skills: {user_skills}")

            users.append(
                UserResponse(
                    id=user.id,
                    name=user.name,
                    department=department_name,
                    yearsOfService=profile.career if profile else 0,
                    skills=user_skills,
                    description=profile.pr if profile else "",
                    joinForm=profile.join_form.name if profile and profile.join_form else "未設定"
                )
            )

        response = DepartmentResponse(name=department_name, users=users)
        print(f"Sending response with {len(users)} users")
        return response

    finally:
        db.close()

# 全部署取得API
@app.get("/departments", response_model=List[DepartmentResponse])
def read_departments():
    db = SessionLocal()
    try:
        departments = db.query(DBDepartment).order_by(DBDepartment.id).all()
        
        department_responses = []
        for department in departments:
            # 部署に所属するユーザーを取得
            users_in_department = (
                db.query(DBUser)
                .join(Profile, DBUser.id == Profile.user_id)
                .join(DBDepartment, Profile.department_id == DBDepartment.id)
                .options(
                    joinedload(DBUser.profile).joinedload(Profile.department),
                    joinedload(DBUser.profile).joinedload(Profile.join_form),
                    joinedload(DBUser.posted_skills).joinedload(PostSkill.skill)
                )
                .filter(DBDepartment.id == department.id)
                .order_by(DBUser.id)  # 一貫した順序で結果を取得
                .distinct()
                .all()
            )
            
            users = []
            for user in users_in_department:
                # ユーザーのスキルを取得
                user_skills = [ps.skill.name for ps in user.posted_skills]
                profile = user.profile
                print(f"Processing user: {user.name} (ID: {user.id}) in {department.name}")
                print(f"Skills: {user_skills}")
                
                users.append(
                    UserResponse(
                        id=user.id,
                        name=user.name,
                        department=department.name,
                        yearsOfService=profile.career if profile else 0,
                        skills=user_skills,
                        description=profile.pr if profile else "",
                        joinForm=profile.join_form.name if profile and profile.join_form else "未設定"
                    )
                )
            
            department_responses.append(DepartmentResponse(name=department.name, users=users))
        
        return department_responses
    
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "Welcome to Chotto API"}


#やまちゃんコード
# ChromaDBの状態を確認する
@app.get("/chroma/status")
def chroma_status():
    """ChromaDBの状態を確認する"""
    try:
        # スキルコレクションのデータを取得
        skills_data = list_collection_items(collection_name="skills")
        skills_count = len(skills_data["ids"]) if skills_data else 0
        
        # プロフィールコレクションのデータを取得
        profiles_data = list_collection_items(collection_name="profiles")
        profiles_count = len(profiles_data["ids"]) if profiles_data else 0
        
        return {
            "status": "ok",
            "collections": {
                "skills": {
                    "count": skills_count,
                    "sample": skills_data["ids"][:5] if skills_count > 0 else []
                },
                "profiles": {
                    "count": profiles_count,
                    "sample": profiles_data["ids"][:5] if profiles_count > 0 else []
                }
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"ChromaDB状態確認エラー: {str(e)}")

# ユーザー詳細取得API
@app.get("/user/{user_id}", response_model=UserResponse)
def read_user(user_id: int):
    db = SessionLocal()
    try:
        # ユーザーを検索（関連するデータも一緒に取得）
        user = (
            db.query(DBUser)
            .join(Profile, DBUser.id == Profile.user_id)
            .join(DBDepartment, Profile.department_id == DBDepartment.id)
            .options(
                joinedload(DBUser.profile).joinedload(Profile.department),
                joinedload(DBUser.profile).joinedload(Profile.join_form),
                joinedload(DBUser.posted_skills).joinedload(PostSkill.skill)
            )
            .filter(DBUser.id == user_id)
            .first()
        )

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # ユーザーのスキルを取得
        skills = [post_skill.skill.name for post_skill in user.posted_skills]
        profile = user.profile

        # デバッグ情報を出力
        print(f"Found user: {user.name} (ID: {user.id})")
        print(f"Department: {profile.department.name if profile and profile.department else '未所属'}")
        print(f"Join Form: {profile.join_form.name if profile and profile.join_form else '未設定'}")
        print(f"Skills: {skills}")

        return UserResponse(
            id=user.id,
            name=user.name,
            department=profile.department.name if profile and profile.department else "未所属",
            yearsOfService=profile.career if profile else 0,
            skills=skills,
            description=profile.pr if profile else "",
            joinForm=profile.join_form.name if profile and profile.join_form else "未設定"
        )

    finally:
        db.close()