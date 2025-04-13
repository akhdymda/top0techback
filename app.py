from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from db_connection.connect_Pinecone import search_similar_skills
from typing import List
from db_connection.connect_MySQL import SessionLocal, get_db
from db_model.tables import SkillMaster, User as DBUser, PostSkill, Department as DBDepartment, Profile, Bookmark
from sqlalchemy.orm import joinedload, Session
from db_model.schemas import SkillMasterBase, SkillResponse, SearchResponse, UserResponse, UserDetailResponse, SearchResult, DepartmentResponse, DepartmentBase, BookmarkResponse, BookmarkListResponse, LoginRequest, LoginResponse
import base64
import bcrypt
import asyncio
from functools import lru_cache
import logging
from contextvars import ContextVar
from fastapi.logger import logger as fastapi_logger
from aiocache import cached, Cache
from aiocache.serializers import PickleSerializer

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("app")

# リクエストIDを追跡するためのコンテキスト変数
request_id_context = ContextVar("request_id", default=None)

app = FastAPI()

# CORSミドルウェア設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では特定のオリジンに制限する
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# リクエストIDミドルウェア
@app.middleware("http")
async def request_id_middleware(request, call_next):
    import uuid
    request_id = str(uuid.uuid4())
    request_id_context.set(request_id)
    response = await call_next(request)
    return response

# パスワードを検証する関数（NextOAuthとの連携用）
def verify_password(plain_password, hashed_password):
    try:
        # 平文パスワードをバイト文字列に変換
        password_bytes = plain_password.encode('utf-8')
        # ハッシュ済みパスワードをバイト文字列に変換
        hashed_bytes = hashed_password.encode('utf-8')
        # bcryptでパスワードを検証
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        logger.error(f"パスワード検証エラー: {e}")
        return False

# スキル検索API
@app.get("/skills/{skill_name}", response_model=SkillResponse)
async def read_skill(skill_name: str):
    logger.info(f"スキル検索 - {skill_name}")
    db = SessionLocal()
    try:
        # スキルを検索
        skill = db.query(SkillMaster).filter(SkillMaster.name == skill_name).first()
        if not skill:
            logger.warning(f"スキル '{skill_name}' は見つかりませんでした")
            raise HTTPException(status_code=404, detail="Skill not found")

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
            .order_by(DBUser.id)  # 一貫した順序で結果を取得
            .distinct()
            .all()
        )

        logger.info(f"スキル '{skill_name}' を持つユーザー: {len(users_with_skill)}人")

        # レスポンス用のユーザーリストを作成
        users = []
        for user in users_with_skill:
            # ユーザーのスキルを取得
            user_skills = [ps.skill.name for ps in user.posted_skills]
            profile = user.profile
            
            # 画像データをBase64エンコード
            image_data = None
            image_data_type = None
            if profile and profile.image_data:
                image_data = base64.b64encode(profile.image_data).decode('utf-8')
                image_data_type = profile.image_data_type
            
            users.append(
                UserResponse(
                    id=user.id,
                    name=user.name,
                    department=profile.department.name if profile and profile.department else "未所属",
                    yearsOfService=profile.career if profile else 0,
                    skills=user_skills,
                    description=profile.pr if profile else "",
                    joinForm=profile.join_form.name if profile and profile.join_form else "未設定",
                    welcome_level=profile.welcome_level.level_name if profile and profile.welcome_level else "未設定",
                    image_data=image_data,
                    image_data_type=image_data_type
                )
            )

        response = SkillResponse(name=skill_name, users=users)
        return response

    finally:
        db.close()

# 全スキル取得API (非同期キャッシュ)
@app.get("/skills", response_model=List[SkillMasterBase])
@cached(ttl=3600)  # 1時間キャッシュ
async def read_skills():
    logger.info("全スキル取得")
    db = SessionLocal()
    try:
        skills = db.query(SkillMaster).all()
        logger.info(f"全スキル取得: {len(skills)}件")
        return [SkillMasterBase(name=skill.name) for skill in skills]
    
    finally:
        db.close()


#ふわっと検索API
@app.get("/search", response_model=SearchResponse)
async def fuzzy_search(query: str, limit: int = 10, db: Session = Depends(get_db)):
    """
    ふわっと検索（ベクトル検索）でユーザーを検索
    """
    logger.info(f"ふわっと検索: クエリ='{query}', 上限={limit}")
    
    try:
        # Pineconeを使用して類似スキルを検索 (非同期化)
        results = await asyncio.to_thread(search_similar_skills, query, limit)
        logger.info(f"Pinecone検索結果: {len(results)}件")

        # 検索結果がない場合
        if not results:
            logger.info(f"'{query}' の検索結果: 0件")
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
                    logger.warning(f"スキルID {skill_id} が見つかりません")
                    continue
                
                # ユーザーIDがある場合は特定のユーザーの情報を取得
                if user_id:
                    user = db.query(DBUser).filter(DBUser.id == user_id).first()
                    if not user:
                        logger.warning(f"ユーザーID {user_id} が見つかりません")
                        continue
                        
                    # 部署情報を取得
                    department_id = None
                    department_name = None
                    if user.profile and user.profile.department_id:
                        department = db.query(DBDepartment).filter(DBDepartment.id == user.profile.department_id).first()
                        if department:
                            department_id = department.id
                            department_name = department.name
                    
                    # 画像データをBase64エンコード
                    image_data = None
                    image_data_type = None
                    if user.profile and user.profile.image_data:
                        image_data = base64.b64encode(user.profile.image_data).decode('utf-8')
                        image_data_type = user.profile.image_data_type
                            
                    # 検索結果を作成
                    search_result = SearchResult(
                        user_id=user.id,
                        user_name=user.name or "名前なし",
                        skill_id=skill.skill_id,
                        skill_name=skill.name,
                        joinForm=user.profile.join_form.name if user.profile and user.profile.join_form else "未設定",
                        description=None,
                        department_id=department_id,
                        department_name=department_name,
                        similarity_score=result.get("score", 0.0),
                        image_data=image_data,
                        image_data_type=image_data_type
                    )
                    search_results.append(search_result)
                
                # ユーザーIDがない場合は、このスキルを持つすべてのユーザーを取得
                else:
                    # スキルに関連付けられたポストスキルを全て取得
                    post_skills = db.query(PostSkill).filter(PostSkill.skill_id == skill_id).all()
                    if not post_skills:
                        logger.warning(f"スキルID {skill_id} に関連するポストスキルが見つかりません")
                        continue
                        
                    # 各ポストスキルからユーザー情報を取得して結果に追加
                    for post_skill in post_skills:
                        user = db.query(DBUser).filter(DBUser.id == post_skill.user_id).first()
                        if not user:
                            logger.warning(f"ユーザーID {post_skill.user_id} が見つかりません")
                            continue
                            
                        # 部署情報を取得
                        department_id = None
                        department_name = None
                        if user.profile and user.profile.department_id:
                            department = db.query(DBDepartment).filter(DBDepartment.id == user.profile.department_id).first()
                            if department:
                                department_id = department.id
                                department_name = department.name
                        
                        # 画像データをBase64エンコード
                        image_data = None
                        image_data_type = None
                        if user.profile and user.profile.image_data:
                            image_data = base64.b64encode(user.profile.image_data).decode('utf-8')
                            image_data_type = user.profile.image_data_type
                        
                        # 検索結果を作成
                        search_result = SearchResult(
                            user_id=user.id,
                            user_name=user.name or "名前なし",
                            skill_id=skill.skill_id,
                            skill_name=skill.name,
                            joinForm=user.profile.join_form.name if user.profile and user.profile.join_form else "未設定",
                            description=None,
                            department_id=department_id,
                            department_name=department_name,
                            similarity_score=result.get("score", 0.0),
                            image_data=image_data,
                            image_data_type=image_data_type
                        )
                        search_results.append(search_result)
        
        logger.info(f"整形後の検索結果: {len(search_results)}件")
        return SearchResponse(
            results = search_results,
            total = len(search_results))
    except Exception as e:
        logger.error(f"検索処理中にエラーが発生: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"検索エラー: {str(e)}")

#部署検索API
@app.get("/departments/{department_name}", response_model=DepartmentResponse)
async def read_department(department_name: str):
    db = SessionLocal()
    try:
        department = db.query(DBDepartment).filter(DBDepartment.name == department_name).first()
        if not department:
            raise HTTPException(status_code=404, detail="Department not found")

        # 所属ユーザーを取得
        users_in_department = (
            db.query(DBUser)
            .join(Profile, DBUser.id == Profile.user_id)
            .options(
                joinedload(DBUser.profile).joinedload(Profile.department),
                joinedload(DBUser.profile).joinedload(Profile.join_form),
                joinedload(DBUser.profile).joinedload(Profile.welcome_level),
                joinedload(DBUser.posted_skills).joinedload(PostSkill.skill)
            )
            .filter(Profile.department_id == department.id)
            .order_by(DBUser.id)  # 一貫した順序で結果を取得
            .all()
        )

        # レスポンス用のユーザーリストを作成
        users = []
        for user in users_in_department:
            # ユーザーのスキルを取得
            user_skills = [ps.skill.name for ps in user.posted_skills]
            profile = user.profile

            # 画像データをBase64エンコード
            image_data = None
            image_data_type = None
            if profile and profile.image_data:
                image_data = base64.b64encode(profile.image_data).decode('utf-8')
                image_data_type = profile.image_data_type

            users.append(
                UserResponse(
                    id=user.id,
                    name=user.name,
                    department=profile.department.name if profile and profile.department else "未所属",
                    yearsOfService=profile.career if profile else 0,
                    skills=user_skills,
                    description=profile.pr if profile else "",
                    joinForm=profile.join_form.name if profile and profile.join_form else "未設定",
                    welcome_level=profile.welcome_level.level_name if profile and profile.welcome_level else "未設定",
                    image_data=image_data,
                    image_data_type=image_data_type
                )
            )

        response = DepartmentResponse(name=department_name, users=users)
        return response

    finally:
        db.close()

# 全部署取得API (非同期キャッシュ)
@app.get("/departments", response_model=List[DepartmentBase])
@cached(ttl=3600)  # 1時間キャッシュ
async def read_departments():
    logger.info("全部署取得")
    db = SessionLocal()
    try:
        departments = db.query(DBDepartment).order_by(DBDepartment.id).all()
        logger.info(f"全部署取得: {len(departments)}件")
        return [DepartmentBase(name=department.name) for department in departments]
    finally:
        db.close()

@app.get("/")
async def read_root():
    return {"message": "Welcome to Chotto API"}

# ユーザー詳細取得API
@app.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user_detail(user_id: int, db: Session = Depends(get_db)):
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

    # 画像データをBase64エンコード
    image_data = None
    image_data_type = None
    if profile and profile.image_data:
        image_data = base64.b64encode(profile.image_data).decode('utf-8')
        image_data_type = profile.image_data_type

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
        image_data=image_data,
        image_data_type=image_data_type,
        welcome_level=profile.welcome_level.level_name if profile and profile.welcome_level else None
    )

# 画像取得用の専用エンドポイント（代替手段として残す）
@app.get("/users/{user_id}/image")
async def get_user_image(user_id: int, db: Session = Depends(get_db)):
    """
    個別に画像データのみを取得するためのエンドポイント。
    メインAPIで画像を取得できるようになったが、軽量化のために別途取得したい場合に使用。
    """
    user = db.query(DBUser).join(Profile, DBUser.id == Profile.user_id).filter(DBUser.id == user_id).first()
    
    if not user or not user.profile or not user.profile.image_data:
        raise HTTPException(status_code=404, detail="User image not found")
    
    image_data = base64.b64encode(user.profile.image_data).decode('utf-8')
    image_data_type = user.profile.image_data_type
    
    return {
        "image_data": image_data,
        "image_data_type": image_data_type
    }

# ブックマーク追加API
@app.post("/bookmarks/{user_id}", response_model=BookmarkResponse)
async def create_bookmark(user_id: int, bookmarked_user_id: int, db: Session = Depends(get_db)):
    # すでにブックマークされているかチェック
    existing_bookmark = db.query(Bookmark).filter(
        Bookmark.bookmarking_user_id == user_id,
        Bookmark.bookmarked_user_id == bookmarked_user_id
    ).first()
    
    if existing_bookmark:
        raise HTTPException(status_code=400, detail="Bookmark already exists")

    # 新しいブックマークを作成
    bookmark = Bookmark(
        bookmarking_user_id=user_id,
        bookmarked_user_id=bookmarked_user_id
    )
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)

    return bookmark

# ブックマーク削除API
@app.delete("/bookmarks/{user_id}", response_model=BookmarkResponse)
async def delete_bookmark(user_id: int, bookmarked_user_id: int, db: Session = Depends(get_db)):
    bookmark = db.query(Bookmark).filter(
        Bookmark.bookmarking_user_id == user_id,
        Bookmark.bookmarked_user_id == bookmarked_user_id
    ).first()

    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    
    db.delete(bookmark)
    db.commit()
    
    return {"message": "Bookmark deleted successfully"}

# ブックマーク一覧取得API
@app.get("/bookmarks/{user_id}", response_model=BookmarkListResponse)
async def get_bookmarks(user_id: int, db: Session = Depends(get_db)):
    bookmarks = (
        db.query(Bookmark)
        .filter(Bookmark.bookmarking_user_id == user_id)
        .options(
            joinedload(Bookmark.bookmarked).joinedload(DBUser.profile).joinedload(Profile.department),
            joinedload(Bookmark.bookmarked).joinedload(DBUser.profile).joinedload(Profile.join_form),
            joinedload(Bookmark.bookmarked).joinedload(DBUser.profile).joinedload(Profile.welcome_level),
            joinedload(Bookmark.bookmarked).joinedload(DBUser.posted_skills).joinedload(PostSkill.skill)
        )
        .all()
    )

    Bookmark_list = []
    for bookmark in bookmarks:
        user = bookmark.bookmarked
        profile = user.profile
        user_skills = [ps.skill.name for ps in user.posted_skills]

        # 画像データをBase64エンコード
        image_data = None
        image_data_type = None
        if profile and profile.image_data:
            image_data = base64.b64encode(profile.image_data).decode('utf-8')
            image_data_type = profile.image_data_type

        Bookmark_list.append(
            BookmarkResponse(
                id=bookmark.id,
                user_id=bookmark.bookmarking_user_id,
                bookmarking_user_id=bookmark.bookmarking_user_id,
                bookmarked_user_id=user.id,
                name=user.name,
                department=profile.department.name if profile and profile.department else "未所属",
                yearsOfService=profile.career if profile else 0,
                skills=user_skills,
                description=profile.pr if profile else "",
                joinForm=profile.join_form.name if profile and profile.join_form else "未設定",
                welcome_level=profile.welcome_level.level_name if profile and profile.welcome_level else "未設定",
                created_at=bookmark.created_at,
                image_data=image_data,
                image_data_type=image_data_type
            ))

    return BookmarkListResponse(bookmarks=Bookmark_list, total=len(Bookmark_list))

# ブックマーク状態確認API
@app.get("/bookmarks/{user_id}/{bookmarked_user_id}/status")
async def check_bookmark_status(user_id: int, bookmarked_user_id: int, db: Session = Depends(get_db)):
    bookmark = db.query(Bookmark).filter(
        Bookmark.bookmarking_user_id == user_id,
        Bookmark.bookmarked_user_id == bookmarked_user_id
    ).first()
    
    return {"is_bookmarked": bookmark is not None}

# ログインAPI
@app.post("/auth/login", response_model=LoginResponse)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """ユーザー認証を行い、認証情報を返す"""
    user = db.query(DBUser).filter(DBUser.email == login_data.email).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="メールアドレスまたはパスワードが正しくありません")
    
    # パスワードの検証
    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="メールアドレスまたはパスワードが正しくありません")
    
    # 認証成功
    return LoginResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        success=True,
        message="認証に成功しました"
    )
    
    