<<<<<<< HEAD
from fastapi import APIRouter, Depends, HTTPException
from db_connection.connect_MySQL import get_db
from db_connection.connect_Chroma import search_similar
from db_connection.embedding import get_text_embedding
from db_model.schemas import SearchResponse, SearchResult
from db_model.tables import PostSkill, User, SkillMaster, Department, Profile
from sqlalchemy.orm import Session

search_router = APIRouter(prefix="/search", tags=["search"])

# ふわっと検索（ベクトル検索）
@search_router.get("/fuzzy", response_model=SearchResponse)
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
                        user = db.query(User).filter(User.id == post_skill.user_id).first()
                        if not user:
                            print(f"ユーザーID {post_skill.user_id} が見つかりません")
                            continue
                            
                        # 部署情報を取得
                        department_id = None
                        department_name = None
                        if user.profile and user.profile.department_id:
                            department = db.query(Department).filter(Department.id == user.profile.department_id).first()
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
                        user = db.query(User).filter(User.id == post_skill.user_id).first()
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
                            department = db.query(Department).filter(Department.id == user.profile.department_id).first()
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
    
# スキル検索
@search_router.get("/skill/{skill_id}", response_model=SearchResponse)
async def search_by_skill(skill_id: int, db: Session = Depends(get_db)):
    """
    特定のスキルを持つユーザーを検索します
    """
    try:
        # スキルの存在確認
        skill = db.query(SkillMaster).filter(SkillMaster.skill_id == skill_id).first()
        if not skill:
            raise HTTPException(status_code=404, detail=f"スキルID {skill_id} は存在しません")
        
        # スキルを持つユーザーを検索
        post_skills = db.query(PostSkill).filter(PostSkill.skill_id == skill_id).all()
        
        search_results = []
        for post_skill in post_skills:
            user = db.query(User).filter(User.id == post_skill.user_id).first()
            if not user:
                continue

            # 部署情報を取得
            department_id = None
            department_name = None
            if user.profile and user.profile.department_id:
                department = db.query(Department).filter(Department.id == user.profile.department_id).first()
                if department:
                    department_id = department.id
                    department_name = department.name
            
            search_result = SearchResult(
                user_id=user.id,
                user_name=user.name or "名前なし",
                skill_id=skill.skill_id,
                skill_name=skill.name,
                description=None,
                department_id=department_id,
                department_name=department_name,
                similarity_score=1.0  # 完全一致
            )
            search_results.append(search_result)
            
            
        return SearchResponse(
            results=search_results,
            total=len(search_results)
        )
    except Exception as e:
        print(f"スキル検索エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"スキル検索エラー: {str(e)}"   )

@search_router.get("/department/{department_id}", response_model=SearchResponse)
async def search_by_department(department_id: int, db: Session = Depends(get_db)):
    """
    特定の部署に所属するユーザーを検索します
    """
    try:
        # 部署の存在確認
        department = db.query(Department).filter(Department.id == department_id).first()
        if not department:
            raise HTTPException(status_code=404, detail=f"部署ID {department_id} は存在しません")
        
        # 部署に所属するユーザーを検索 (Profileテーブル経由)
        profiles = db.query(Profile).filter(Profile.department_id == department_id).all()
        
        search_results = []
        for profile in profiles:
            user = db.query(User).filter(User.id == profile.user_id).first()
            if not user:
                continue
            
            # ユーザーの主要スキルを取得（存在すれば）
            post_skill = db.query(PostSkill).filter(PostSkill.user_id == user.id).first()
            skill_id = None
            skill_name = None
            description = None
            
            if post_skill:
                skill = db.query(SkillMaster).filter(SkillMaster.id == post_skill.skill_id).first()
                if skill:
                    skill_id = skill.id
                    skill_name = skill.name
                    description = post_skill.description
            
            search_result = SearchResult(
                user_id=user.id,
                user_name=user.name or "名前なし",
                skill_id=skill_id,
                skill_name=skill_name,
                description=description,
                department_id=department.id,
                department_name=department.name,
                similarity_score=1.0  # 完全一致
            )
            search_results.append(search_result)
        
        return SearchResponse(
            results=search_results,
            total=len(search_results)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"部署検索エラー: {str(e)}") 
=======
# from fastapi import APIRouter, Depends, HTTPException
# from db_connection.connect_MySQL import get_db
# from db_connection.connect_Chroma import search_similar
# from db_connection.embedding import get_text_embedding
# from db_model.schemas import SearchResponse, SearchResult
# from db_model.tables import PostSkill, User, SkillMaster, Department, Profile
# from sqlalchemy.orm import Session

# search_router = APIRouter(prefix="/search", tags=["search"])

# ふわっと検索（ベクトル検索）
# @search_router.get("/fuzzy", response_model=SearchResponse)
# async def fuzzy_search(query: str, limit: int = 5, db: Session = Depends(get_db)):
#    """
#    ふわっと検索（ベクトル検索）でユーザーを検索
#    """
#    print(f"検索クエリ: {query}, 取得件数上限: {limit}")
    
#    try:
        # テキストからエンベディングを生成
#        embedding = get_text_embedding(query)
#        print(f"エンベディング生成完了。次元数: {len(embedding)}")

        # ChromaDBで類似検索を実行
#        results = search_similar(embedding, limit=limit)
#        print(f"ChromaDB検索結果: {results}")

        # 検索結果がない場合
#        if not results or not results.get("ids") or len(results["ids"][0]) == 0:
#            print("検索結果なし")
#            return SearchResponse(results=[], total=0)
        
#        print(f"検索結果の件数: {len(results['ids'][0])}")
        
        # 結果をフォーマット
#        search_results = []
#        for i, id_str in enumerate(results["ids"][0]):
#            print(f"処理中のID: {id_str}")
            
            # IDの形式を確認
#            if id_str.startswith("skill_"):
                # skill_1 形式の場合は数字部分を抽出
#                try:
#                    skill_id = int(id_str.split("_")[1])
#                    print(f"スキルIDに変換: {skill_id}")
#                    
                    # スキルマスターからスキル情報を取得
#                    skill = db.query(SkillMaster).filter(SkillMaster.skill_id == skill_id).first()
#                    if not skill:
#                        print(f"スキルID {skill_id} が見つかりません")
#                        continue
                        
                    # スキルに関連付けられたポストスキルを全て取得
#                    post_skills = db.query(PostSkill).filter(PostSkill.skill_id == skill_id).all()
#                    if not post_skills:
#                        print(f"スキルID {skill_id} に関連するポストスキルが見つかりません")
#                        continue
                        
                    # 各ポストスキルからユーザー情報を取得して結果に追加
#                    for post_skill in post_skills:
#                        user = db.query(User).filter(User.id == post_skill.user_id).first()
#                        if not user:
#                            print(f"ユーザーID {post_skill.user_id} が見つかりません")
#                            continue
                            
                        # 部署情報を取得
#                        department_id = None
#                        department_name = None
#                        if user.profile and user.profile.department_id:
#                            department = db.query(Department).filter(Department.id == user.profile.department_id).first()
#                            if department:
#                                department_id = department.id
#                                department_name = department.name
                        
                        # 検索結果を作成
#                        search_result = SearchResult(
#                            user_id=user.id,
#                            user_name=user.name or "名前なし",
#                            skill_id=skill.skill_id,
#                            skill_name=skill.name,
#                            description=None,  # description フィールドは削除されましたが、スキーマとの整合性のために None を設定
#                            department_id=department_id,
#                            department_name=department_name,
#                            similarity_score=results["distances"][0][i] if "distances" in results else 0.0
#                        )
#                        search_results.append(search_result)
#                except Exception as e:
#                    print(f"スキルID '{id_str}' の処理中にエラー: {str(e)}")
#                    continue
#            else:
                # 通常の数値IDとして処理を試みる
#                try:
#                    skill_id_int = int(id_str)
#                    print(f"ポストスキルIDとして処理: {skill_id_int}")
#                    
#                    # データベースから投稿スキル情報を取得
#                    post_skill = db.query(PostSkill).filter(PostSkill.id == skill_id_int).first()
#                    if post_skill:
#                        print(f"ポストスキル: user_id={post_skill.user_id}, skill_id={post_skill.skill_id}")
                        
                        # ユーザー情報を取得
#                        user = db.query(User).filter(User.id == post_skill.user_id).first()
#                        if not user:
#                            print(f"ユーザーID {post_skill.user_id} が見つかりません")
#                            continue

                        # スキル情報を取得
#                        skill = db.query(SkillMaster).filter(SkillMaster.skill_id == post_skill.skill_id).first()
#                        if not skill:
#                            print(f"スキルID {post_skill.skill_id} が見つかりません")
#                            continue

                        # 部署情報を取得
#                        department_id = None
#                        department_name = None
#                        if user.profile and user.profile.department_id:
#                            department = db.query(Department).filter(Department.id == user.profile.department_id).first()
#                            if department:
#                                department_id = department.id
#                                department_name = department.name
                        
                        # 検索結果を作成
#                        search_result = SearchResult(
#                            user_id=user.id,
#                            user_name=user.name or "名前なし",
#                            skill_id=skill.skill_id,
#                            skill_name=skill.name,
#                            description=None,  # description フィールドは削除されましたが、スキーマとの整合性のために None を設定
#                            department_id=department_id,
#                            department_name=department_name,
#                            similarity_score=results["distances"][0][i] if "distances" in results else 0.0
#                        )
#                        search_results.append(search_result)
#                    else:
#                        print(f"ID {id_str} に対応するポストスキルが見つかりません")
#                except Exception as e:
#                    print(f"ID '{id_str}' の処理中にエラー: {str(e)}")
#                    continue
                
#        print(f"整形後の検索結果: {len(search_results)}件")
#        return SearchResponse(
#            results = search_results,
#            total = len(search_results))
#    except Exception as e:
#        print(f"検索処理中にエラーが発生: {str(e)}")
#        import traceback
#        traceback.print_exc()
#        raise HTTPException(status_code=500, detail=f"検索エラー: {str(e)}")
    
# スキル検索
# @search_router.get("/skill/{skill_id}", response_model=SearchResponse)
# async def search_by_skill(skill_id: int, db: Session = Depends(get_db)):
#    """
#    特定のスキルを持つユーザーを検索します
#    """
#    try:
        # スキルの存在確認
#        skill = db.query(SkillMaster).filter(SkillMaster.skill_id == skill_id).first()
#        if not skill:
#            raise HTTPException(status_code=404, detail=f"スキルID {skill_id} は存在しません")
        
        # スキルを持つユーザーを検索
#        post_skills = db.query(PostSkill).filter(PostSkill.skill_id == skill_id).all()
        
#        search_results = []
#        for post_skill in post_skills:
#            user = db.query(User).filter(User.id == post_skill.user_id).first()
#            if not user:
#                continue

            # 部署情報を取得
#            department_id = None
#            department_name = None
#            if user.profile and user.profile.department_id:
#                department = db.query(Department).filter(Department.id == user.profile.department_id).first()
#                if department:
#                    department_id = department.id
#                    department_name = department.name
            
#            search_result = SearchResult(
#                user_id=user.id,
#                user_name=user.name or "名前なし",
#                skill_id=skill.skill_id,
#                skill_name=skill.name,
#                description=None,
#                department_id=department_id,
#                department_name=department_name,
#                similarity_score=1.0  # 完全一致
#            )
#            search_results.append(search_result)
            
            
#        return SearchResponse(
#            results=search_results,
#            total=len(search_results)
#        )
#    except Exception as e:
#        print(f"スキル検索エラー: {str(e)}")
#        raise HTTPException(status_code=500, detail=f"スキル検索エラー: {str(e)}"   )

# @search_router.get("/department/{department_id}", response_model=SearchResponse)
# async def search_by_department(department_id: int, db: Session = Depends(get_db)):
#    """
#    特定の部署に所属するユーザーを検索します
#    """
#    try:
        # 部署の存在確認
#        department = db.query(Department).filter(Department.id == department_id).first()
#        if not department:
#            raise HTTPException(status_code=404, detail=f"部署ID {department_id} は存在しません")
        
        # 部署に所属するユーザーを検索 (Profileテーブル経由)
#        profiles = db.query(Profile).filter(Profile.department_id == department_id).all()
        
#        search_results = []
#        for profile in profiles:
#            user = db.query(User).filter(User.id == profile.user_id).first()
#            if not user:
#                continue
            
            # ユーザーの主要スキルを取得（存在すれば）
#            post_skill = db.query(PostSkill).filter(PostSkill.user_id == user.id).first()
#            skill_id = None
#            skill_name = None
#            description = None
            
#            if post_skill:
#                skill = db.query(SkillMaster).filter(SkillMaster.id == post_skill.skill_id).first()
#                if skill:
#                    skill_id = skill.id
#                    skill_name = skill.name
#                    description = post_skill.description
            
#            search_result = SearchResult(
#                user_id=user.id,
#                user_name=user.name or "名前なし",
#                skill_id=skill_id,
#                skill_name=skill_name,
#                description=description,
#                department_id=department.id,
#                department_name=department.name,
#                similarity_score=1.0  # 完全一致
#            )
#            search_results.append(search_result)
        
#        return SearchResponse(
#            results=search_results,
#            total=len(search_results)
#        )
#    except HTTPException:
#        raise
#    except Exception as e:
#        raise HTTPException(status_code=500, detail=f"部署検索エラー: {str(e)}") 
>>>>>>> main
