from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from db_connection.connect_Chroma import list_collection_items
from db_crud.search import search_router
from pydantic import BaseModel
from typing import List
from db_connection.connect_MySQL import SessionLocal
from db_model.tables import SkillMaster, User as DBUser, PostSkill, Department as DBDepartment, Profile
from sqlalchemy.orm import joinedload

app = FastAPI()

# CORSミドルウェア設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では特定のオリジンに制限する
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DBセッション用のDependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# @app.get("/search")
# def search_users(q: str = Query(..., min_length=1)):
#     # 例: 名前やスキルの一部に q が含まれるデータを返す
#     all_users = crud.myselectAll(mymodels.Customers)

#     if not all_users:
#         return []

#     all_users_obj = json.loads(all_users)

#     # 検索語が名前またはdescriptionに含まれるユーザーをフィルタ
#     matched_users = [
#         user for user in all_users_obj
#         if q.lower() in user.get("customer_name", "").lower()
#         or q.lower() in user.get("description", "").lower()
#     ]

#     return matched_users



# @app.get("/")
# def index():
#     return {"message": "FastAPI top page!"}




# @app.post("/customers")
# def create_customer(customer: Customer):
#     values = customer.dict()
#     tmp = crud.myinsert(mymodels.Customers, values)
#     result = crud.myselect(mymodels.Customers, values.get("customer_id"))

#     if result:
#         result_obj = json.loads(result)
#         return result_obj if result_obj else None
#     return None


# @app.get("/customers")
# def read_one_customer(customer_id: str = Query(...)):
#     result = crud.myselect(mymodels.Customers, customer_id)
#     if not result:
#         raise HTTPException(status_code=404, detail="Customer not found")
#     result_obj = json.loads(result)
#     return result_obj[0] if result_obj else None

# @app.get("/allcustomers")
# def read_all_customer():
#     result = crud.myselectAll(mymodels.Customers)
#     # 結果がNoneの場合は空配列を返す
#     if not result:
#         return []
#     # JSON文字列をPythonオブジェクトに変換
#     return json.loads(result)


# @app.put("/customers")
# def update_customer(customer: Customer):
#     values = customer.dict()
#     values_original = values.copy()
#     tmp = crud.myupdate(mymodels.Customers, values)
#     result = crud.myselect(mymodels.Customers, values_original.get("customer_id"))
#     if not result:
#         raise HTTPException(status_code=404, detail="Customer not found")
#     result_obj = json.loads(result)
#     return result_obj[0] if result_obj else None


# @app.delete("/customers")
# def delete_customer(customer_id: str = Query(...)):
#     result = crud.mydelete(mymodels.Customers, customer_id)
#     if not result:
#         raise HTTPException(status_code=404, detail="Customer not found")
#     return {"customer_id": customer_id, "status": "deleted"}


# @app.get("/fetchtest")
# def fetchtest():
#     response = requests.get('https://jsonplaceholder.typicode.com/users')
#     return response.json()

#仮ユーザーDB
# class User(BaseModel):
#     id: int
#     name: str
#     department: str
#     yearsOfService: int
#     skills: List[str]
#     description: str

# def get_users_from_db() -> List[User]:
#     return [
#         User(
#             id=1,
#             name="高橋健人",
#             department="リビング電気部",
#             yearsOfService=13,
#             skills=["Webマーケティング全般", "データ分析と計測", "コンテンツマーケティング", "SNSマーケティング"],
#             description="経験豊富で技術にも強いマーケターです。"
#         ),
#         User(
#             id=2,
#             name="佐藤美咲",
#             department="企画部",
#             yearsOfService=8,
#             skills=["新規事業企画", "社内プレゼン", "市場調査"],
#             description="企画力と調整力に優れたリーダー型社員です。"
#         ),
#         User(
#             id=3,
#             name="田中陽介",
#             department="エネルギー事業革新部",
#             yearsOfService=5,
#             skills=["IoT", "電力管理", "スマートホーム"],
#             description="最新技術に強く、若手ながらも信頼される技術者です。"
#         ),
#         User(
#             id=4,
#             name="中村翔太",
#             department="WEBソリューションプロジェクト部",
#             yearsOfService=10,
#             skills=["Web開発", "UI/UX設計", "SEO"],
#             description="ユーザー視点でサービス設計を行うWeb系エンジニアです。"
#         ),
#     ]

# APIレスポンス用のUserモデル
class UserResponse(BaseModel):
    id: int
    name: str
    department: str
    yearsOfService: int
    skills: List[str]
    description: str
    joinForm: str  # 入社形態を追加

    class Config:
        from_attributes = True

# APIレスポンス用のスキルモデル
class SkillResponse(BaseModel):
    name: str
    users: List[UserResponse] = []

    class Config:
        from_attributes = True

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

# #仮部署DB
# class Department(BaseModel):
#     name: str
#     users: List[User] = []  # ユーザー情報を含めるように修正

# def get_departments_from_db() -> List[Department]:
#     all_users = get_users_from_db()
#     departments = [
#         Department(name="企画部"),
#         Department(name="設備ソリューション事業部"),
#         Department(name="リビング相談部"),
#         Department(name="総合設備事業部"),
#         Department(name="リビング営業部"),
#         Department(name="BTMソリューションプロジェクト部"),
#         Department(name="エネルギー事業革新部"),
#         Department(name="WEBソリューションプロジェクト部"),
#         Department(name="リビング業務改革部"),
#         Department(name="ソリューション共創本部"),
#     ]
    
#     # 各部署に所属するユーザーを設定
#     for dept in departments:
#         dept.users = [user for user in all_users if user.department == dept.name]
    
#     return departments


#ふわっと検索API
@app.get("/search", response_model=List[UserResponse])
def search_users(q: str = Query(..., min_length=1)):
    print(f"🔍 受け取ったクエリ: {q}", flush=True)
    
    db = SessionLocal()
    try:
        # ユーザーを検索（名前で部分一致）
        users = (
            db.query(DBUser)
            .join(Profile)
            .options(joinedload(DBUser.posted_skills).joinedload(PostSkill.skill))
            .filter(DBUser.name.ilike(f"%{q}%"))
            .all()
        )
        
        # レスポンス用のユーザーリストを作成
        user_responses = []
        for user in users:
            user_skills = [ps.skill.name for ps in user.posted_skills]
            profile = user.profile
            
            user_responses.append(
                UserResponse(
                    id=user.id,
                    name=user.name,
                    department=profile.department.name if profile and profile.department else "",
                    yearsOfService=profile.career if profile else 0,
                    skills=user_skills,
                    description=profile.pr if profile else "",
                    joinForm=profile.join_form.name if profile and profile.join_form else "未設定"  # 入社形態を追加
                )
            )
        
        return user_responses
    
    finally:
        db.close()

# APIレスポンス用の部署モデル
class DepartmentResponse(BaseModel):
    name: str
    users: List[UserResponse] = []

    class Config:
        from_attributes = True

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

# ルーター登録
app.include_router(search_router)

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
