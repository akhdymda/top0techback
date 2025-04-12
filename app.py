from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from db_connection.connect_Pinecone import search_similar_skills
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from db_connection.connect_MySQL import SessionLocal, get_db
from db_model.tables import SkillMaster, User as DBUser, PostSkill, Department as DBDepartment, Profile, Bookmark
from sqlalchemy.orm import joinedload, Session
from db_model.schemas import SkillMasterBase, SkillResponse, SearchResponse, UserResponse, SearchResult, DepartmentResponse, DepartmentBase, BookmarkResponse, BookmarkCreate
from db_connection.embedding import get_text_embedding
import signal
import sys
from datetime import datetime
import base64

app = FastAPI()

# CORSミドルウェア設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では特定のオリジンに制限する
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# シンプルな部署レスポンスモデル
class SimpleDepartmentResponse(BaseModel):
    name: str

    model_config = {
        "from_attributes": True
    }

# シンプルなスキルレスポンスモデル
class SimpleSkillResponse(BaseModel):
    name: str

    model_config = {
        "from_attributes": True
    }

# ユーザー情報のレスポンスモデル
class UserResponse(BaseModel):
    id: int
    name: str
    department: str
    yearsOfService: int
    skills: List[str]
    description: str
    joinForm: str
    welcome_level: Optional[str] = None
    imageUrl: Optional[str] = None

    model_config = {
        "from_attributes": True
    }

# スキル検索のレスポンスモデル
class SkillResponse(BaseModel):
    name: str
    users: List[UserResponse]

    model_config = {
        "from_attributes": True
    }

# 部署検索のレスポンスモデル
class DepartmentResponse(BaseModel):
    name: str
    users: List[UserResponse]

    model_config = {
        "from_attributes": True
    }

# ブックマークのレスポンスモデル
class BookmarkResponse(BaseModel):
    id: int
    user_id: int
    bookmarked_user_id: int
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

# ブックマーク一覧のレスポンスモデル
class BookmarkListResponse(BaseModel):
    bookmarks: List[Dict[str, Any]]

    model_config = {
        "from_attributes": True
    }

# ユーザー詳細のレスポンスモデル
class UserDetailResponse(BaseModel):
    id: int
    name: str
    department: str
    position: str
    yearsOfService: int
    joinForm: str
    skills: List[str]
    experiences: List[Dict[str, str]]
    description: Optional[str] = None
    imageUrl: Optional[str] = None
    welcome_level: Optional[str] = None

    model_config = {
        "from_attributes": True
    }

# ユーザー検索のレスポンスモデル
class UserSearchResponse(BaseModel):
    id: int
    name: str
    department: str
    yearsOfService: int
    skills: List[str]
    description: Optional[str] = None
    imageUrl: Optional[str] = None
    welcome_level: Optional[str] = None
    similarity_score: Optional[float] = None

    model_config = {
        "from_attributes": True
    }

# スキル検索API
@app.get("/skills/{skill_name}", response_model=SkillResponse)
def read_skill(skill_name: str):
    db = SessionLocal()
    try:
        print(f"スキル検索開始: {skill_name}")
        
        # スキルを検索
        skill = db.query(SkillMaster).filter(SkillMaster.name == skill_name).first()
        if not skill:
            print(f"スキルが見つかりません: {skill_name}")
            raise HTTPException(status_code=404, detail="Skill not found")

        print(f"スキルが見つかりました: {skill.name} (ID: {skill.skill_id})")

        # スキルを持つユーザーを取得
        users_with_skill = (
            db.query(DBUser)
            .join(PostSkill, DBUser.id == PostSkill.user_id)
            .join(Profile, DBUser.id == Profile.user_id)
            .join(DBDepartment, Profile.department_id == DBDepartment.id)
            .options(
                joinedload(DBUser.profile).joinedload(Profile.department),
                joinedload(DBUser.profile).joinedload(Profile.join_form),
                joinedload(DBUser.profile).joinedload(Profile.welcome_level),
                joinedload(DBUser.posted_skills).joinedload(PostSkill.skill)
            )
            .filter(PostSkill.skill_id == skill.skill_id)
            .order_by(DBUser.id)
            .distinct()
            .all()
        )

        print(f"スキルを持つユーザー数: {len(users_with_skill)}")

        # レスポンス用のユーザーリストを作成
        users = []
        for user in users_with_skill:
            # ユーザーのスキルを取得
            user_skills = [ps.skill.name for ps in user.posted_skills]
            profile = user.profile
            
            # 画像データの処理
            image_url = None
            if profile and profile.image_data and profile.image_data_type:
                try:
                    encoded_image = base64.b64encode(profile.image_data).decode('utf-8')
                    image_url = f"data:{profile.image_data_type};base64,{encoded_image}"
                    print(f"画像データを処理しました: サイズ={len(profile.image_data)}バイト, タイプ={profile.image_data_type}")
                except Exception as e:
                    print(f"画像データの処理中にエラーが発生: {str(e)}")
                    image_url = None
            
            # デバッグ情報を追加
            print(f"ユーザー処理中: {user.name} (ID: {user.id})")
            print(f"部署: {profile.department.name if profile and profile.department else '未所属'}")
            print(f"入社形態: {profile.join_form.name if profile and profile.join_form else '未設定'}")
            print(f"スキル: {user_skills}")

            user_response = UserResponse(
                id=user.id,
                name=user.name,
                department=profile.department.name if profile and profile.department else "未所属",
                yearsOfService=profile.career if profile else 0,
                skills=user_skills,
                description=profile.pr if profile else "",
                joinForm=profile.join_form.name if profile and profile.join_form else "未設定",
                welcome_level=profile.welcome_level.level_name if profile and profile.welcome_level else None,
                imageUrl=image_url
            )
            users.append(user_response)

        response = SkillResponse(name=skill_name, users=users)
        print(f"レスポンス送信: {len(users)} ユーザー")
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
    
    if not query:
        print("エラー: 検索クエリが空です")
        return SearchResponse(results=[], total=0)
    
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
        return SearchResponse(results=[], total=0)

#部署検索API
@app.get("/departments/{department_name}", response_model=DepartmentResponse)
def read_department(department_name: str):
    db = SessionLocal()
    try:
        print(f"部署検索開始: {department_name}")
        
        # 部署を検索
        department = db.query(DBDepartment).filter(DBDepartment.name == department_name).first()
        if not department:
            print(f"部署が見つかりません: {department_name}")
            raise HTTPException(status_code=404, detail="Department not found")

        print(f"部署が見つかりました: {department.name} (ID: {department.id})")

        # 部署に所属するユーザーを取得
        users_in_department = (
            db.query(DBUser)
            .join(Profile, DBUser.id == Profile.user_id)
            .join(DBDepartment, Profile.department_id == DBDepartment.id)
            .options(
                joinedload(DBUser.profile).joinedload(Profile.department),
                joinedload(DBUser.profile).joinedload(Profile.join_form),
                joinedload(DBUser.profile).joinedload(Profile.welcome_level),
                joinedload(DBUser.posted_skills).joinedload(PostSkill.skill)
            )
            .filter(DBDepartment.id == department.id)
            .order_by(DBUser.id)
            .distinct()
            .all()
        )

        print(f"部署に所属するユーザー数: {len(users_in_department)}")

        # レスポンス用のユーザーリストを作成
        users = []
        for user in users_in_department:
            # ユーザーのスキルを取得
            user_skills = [ps.skill.name for ps in user.posted_skills]
            profile = user.profile
            
            # 画像データの処理
            image_url = None
            if profile and profile.image_data and profile.image_data_type:
                try:
                    encoded_image = base64.b64encode(profile.image_data).decode('utf-8')
                    image_url = f"data:{profile.image_data_type};base64,{encoded_image}"
                    print(f"画像データを処理しました: サイズ={len(profile.image_data)}バイト, タイプ={profile.image_data_type}")
                except Exception as e:
                    print(f"画像データの処理中にエラーが発生: {str(e)}")
                    image_url = None
            
            # デバッグ情報を追加
            print(f"ユーザー処理中: {user.name} (ID: {user.id})")
            print(f"部署: {department_name}")
            print(f"入社形態: {profile.join_form.name if profile and profile.join_form else '未設定'}")
            print(f"スキル: {user_skills}")

            user_response = UserResponse(
                id=user.id,
                name=user.name,
                department=department_name,
                yearsOfService=profile.career if profile else 0,
                skills=user_skills,
                description=profile.pr if profile else "",
                joinForm=profile.join_form.name if profile and profile.join_form else "未設定",
                welcome_level=profile.welcome_level.level_name if profile and profile.welcome_level else None,
                imageUrl=image_url
            )
            users.append(user_response)

        response = DepartmentResponse(name=department_name, users=users)
        print(f"レスポンス送信: {len(users)} ユーザー")
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
@app.get("/users/{user_id}", response_model=UserDetailResponse)
def get_user_detail(user_id: int, db: Session = Depends(get_db)):
    user = (
        db.query(DBUser)
        .join(Profile, DBUser.id == Profile.user_id)
        .join(DBDepartment, Profile.department_id == DBDepartment.id)
        .options(
            joinedload(DBUser.profile).joinedload(Profile.department),
            joinedload(DBUser.profile).joinedload(Profile.join_form),
            joinedload(DBUser.profile).joinedload(Profile.welcome_level),
            joinedload(DBUser.posted_skills).joinedload(PostSkill.skill)
        )
        .filter(DBUser.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    profile = user.profile
    user_skills = [ps.skill.name for ps in user.posted_skills]

    # 画像データの処理
    image_url = None
    if profile and profile.image_data and profile.image_data_type:
        try:
            # Base64エンコードして、データURIスキーマを作成
            encoded_image = base64.b64encode(profile.image_data).decode('utf-8')
            image_url = f"data:{profile.image_data_type};base64,{encoded_image}"
            print(f"画像データを処理しました: サイズ={len(profile.image_data)}バイト, タイプ={profile.image_data_type}")
        except Exception as e:
            print(f"画像データの処理中にエラーが発生: {str(e)}")
            image_url = None

    # 経験・実績のダミーデータ
    experiences = [
        {
            "title": "大規模プロジェクトのマネジメント",
            "description": "100人規模のチームで新規サービスの立ち上げを担当。スケジュール管理からリスク管理まで一貫して対応。"
        },
        {
            "title": "マーケティング戦略の立案と実行",
            "description": "複数の新規サービスのマーケティング戦略を担当。ユーザー獲得からブランディングまで幅広く対応。"
        }
    ]

    return UserDetailResponse(
        id=user.id,
        name=user.name,
        department=profile.department.name if profile and profile.department else "未所属",
        position="マーケティング部 / プロジェクトマネージャー",  # ダミーデータ
        yearsOfService=profile.career if profile else 0,
        joinForm=profile.join_form.name if profile and profile.join_form else "未設定",
        skills=user_skills,
        experiences=experiences,
        description=profile.pr if profile else None,
        imageUrl=image_url,
        welcome_level=profile.welcome_level.level_name if profile and profile.welcome_level else None
    )

# ブックマーク追加API
@app.post("/bookmarks/{user_id}/{bookmarked_user_id}", response_model=BookmarkResponse)
def create_bookmark(user_id: int, bookmarked_user_id: int, db: Session = Depends(get_db)):
    # 既存のブックマークをチェック
    existing_bookmark = db.query(Bookmark).filter(
        Bookmark.user_id == user_id,
        Bookmark.bookmarked_user_id == bookmarked_user_id
    ).first()
    
    if existing_bookmark:
        raise HTTPException(status_code=400, detail="Already bookmarked")
    
    # 新しいブックマークを作成
    bookmark = Bookmark(
        user_id=user_id,
        bookmarked_user_id=bookmarked_user_id
    )
    
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)
    
    return bookmark

# ブックマーク削除API
@app.delete("/bookmarks/{user_id}/{bookmarked_user_id}")
def delete_bookmark(user_id: int, bookmarked_user_id: int, db: Session = Depends(get_db)):
    bookmark = db.query(Bookmark).filter(
        Bookmark.user_id == user_id,
        Bookmark.bookmarked_user_id == bookmarked_user_id
    ).first()
    
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    
    db.delete(bookmark)
    db.commit()
    
    return {"message": "Bookmark deleted successfully"}

# ブックマーク一覧取得API
@app.get("/bookmarks/{user_id}", response_model=BookmarkListResponse)
def get_bookmarks(user_id: int, db: Session = Depends(get_db)):
    bookmarks = (
        db.query(Bookmark)
        .join(DBUser, Bookmark.bookmarked_user_id == DBUser.id)
        .join(Profile, DBUser.id == Profile.user_id)
        .join(DBDepartment, Profile.department_id == DBDepartment.id)
        .options(
            joinedload(Bookmark.bookmarked_user).joinedload(DBUser.profile).joinedload(Profile.department),
            joinedload(Bookmark.bookmarked_user).joinedload(DBUser.profile).joinedload(Profile.join_form),
            joinedload(Bookmark.bookmarked_user).joinedload(DBUser.posted_skills).joinedload(PostSkill.skill)
        )
        .filter(Bookmark.user_id == user_id)
        .all()
    )
    
    bookmark_list = []
    for bookmark in bookmarks:
        user = bookmark.bookmarked_user
        profile = user.profile
        user_skills = [ps.skill.name for ps in user.posted_skills]
        
        bookmark_list.append({
            "id": bookmark.id,
            "user_id": user.id,
            "name": user.name,
            "department": profile.department.name if profile and profile.department else "未所属",
            "yearsOfService": profile.career if profile else 0,
            "skills": user_skills,
            "description": profile.pr if profile else "",
            "joinForm": profile.join_form.name if profile and profile.join_form else "未設定",
            "created_at": bookmark.created_at
        })
    
    return BookmarkListResponse(bookmarks=bookmark_list)

# ブックマーク状態確認API
@app.get("/bookmarks/{user_id}/{bookmarked_user_id}/status")
def check_bookmark_status(user_id: int, bookmarked_user_id: int, db: Session = Depends(get_db)):
    bookmark = db.query(Bookmark).filter(
        Bookmark.user_id == user_id,
        Bookmark.bookmarked_user_id == bookmarked_user_id
    ).first()
    
    return {"is_bookmarked": bookmark is not None}

def signal_handler(sig, frame):
    print("\nサーバーを停止します...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)