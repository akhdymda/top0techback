from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from db_connection.connect_Chroma import list_collection_items
from db_crud.search import search_router

app = FastAPI()

# CORSミドルウェア設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では特定のオリジンに制限する
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーター登録
app.include_router(search_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to Chotto API"}

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