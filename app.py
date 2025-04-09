from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from db_connection.connect_Pinecone import search_similar_skills
from pydantic import BaseModel
from typing import List
from db_connection.connect_MySQL import SessionLocal, get_db
from db_model.tables import SkillMaster, User as DBUser, PostSkill, Department as DBDepartment, Profile, Bookmark
from sqlalchemy.orm import joinedload, Session
from db_model.schemas import SkillMasterBase, SkillResponse, SearchResponse, UserResponse, SearchResult, DepartmentResponse, DepartmentBase, BookmarkResponse, BookmarkCreate
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
@app.get("/skills", response_model=List[SkillMasterBase])
def read_skills():
    db = SessionLocal()
    try:
        skills = db.query(SkillMaster).all()
        return [SkillMasterBase(name=skill.name) for skill in skills]
    
    finally:
        db.close()


#ふわっと検索API
@app.get("/search", response_model=SearchResponse)
async def fuzzy_search(query: str, limit: int = 10, db: Session = Depends(get_db)):
    """
    ふわっと検索（ベクトル検索）でユーザーを検索
    """
    print(f"検索クエリ: {query}, 取得件数上限: {limit}")
    
    try:
        # Pineconeを使用して類似スキルを検索
        results = search_similar_skills(query, limit=limit)
        print(f"Pinecone検索結果: {len(results)}件")

        # 検索結果がない場合
        if not results:
            print("検索結果なし")
            return SearchResponse(results=[], total=0)
        
        # 結果をフォーマット
        search_results = []
        for result in results:
            skill_id = result.get("skill_id")
            user_id = result.get("user_id")
            
            # スキルIDがある場合
            if skill_id:
                # スキルマスターからスキル情報を取得
                skill = db.query(SkillMaster).filter(SkillMaster.skill_id == skill_id).first()
                if not skill:
                    print(f"スキルID {skill_id} が見つかりません")
                    continue
                
                # ユーザーIDがある場合は特定のユーザーの情報を取得
                if user_id:
                    user = db.query(DBUser).filter(DBUser.id == user_id).first()
                    if not user:
                        print(f"ユーザーID {user_id} が見つかりません")
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
                        description=None,
                        department_id=department_id,
                        department_name=department_name,
                        similarity_score=result.get("score", 0.0)
                    )
                    search_results.append(search_result)
                
                # ユーザーIDがない場合は、このスキルを持つすべてのユーザーを取得
                else:
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
                            description=None,
                            department_id=department_id,
                            department_name=department_name,
                            similarity_score=result.get("score", 0.0)
                        )
                        search_results.append(search_result)
        
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
@app.get("/departments", response_model=List[DepartmentBase])
def read_departments():
    db = SessionLocal()
    try:
        departments = db.query(DBDepartment).order_by(DBDepartment.id).all()
        return [DepartmentBase(name=department.name) for department in departments]
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "Welcome to Chotto API"}

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