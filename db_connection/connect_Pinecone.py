import os
from dotenv import load_dotenv
from functools import lru_cache
from pathlib import Path
from pinecone import Pinecone, ServerlessSpec
from db_connection.embedding import get_text_embedding

# 環境変数の読み込み
base_path = Path(__file__).parents[1]  # backendディレクトリへのパス
env_path = base_path / '.env'
load_dotenv(dotenv_path=env_path)

# Pinecone APIキーとインデックス名
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "gcp-starter")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "skills-index")

# 埋め込みモデル（OpenAI）を設定
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "text-embedding-ada-002")

# Pineconeクライアントとインデックスのシングルトンインスタンス
_pinecone_client = None
_pinecone_index = None

@lru_cache
def get_pinecone_client():
    """Pineconeクライアントのシングルトンインスタンスを返す"""
    global _pinecone_client, _pinecone_index
    
    if _pinecone_index is not None:
        return _pinecone_index
    
    if not PINECONE_API_KEY:
        raise ValueError("PINECONE_API_KEYが設定されていません")
    
    try:
        # Pineconeクライアントの初期化（新APIバージョン）
        _pinecone_client = Pinecone(api_key=PINECONE_API_KEY)
        
        # インデックスの存在確認
        index_list = [index.name for index in _pinecone_client.list_indexes()]
        
        # インデックスが存在しない場合、作成
        if PINECONE_INDEX_NAME not in index_list:
            _pinecone_client.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=1536,  # OpenAIのデフォルト埋め込みサイズ
                metric="cosine",  # コサイン類似度を使用
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
            print(f"Pineconeインデックス '{PINECONE_INDEX_NAME}' を作成しました")
        
        _pinecone_index = _pinecone_client.Index(PINECONE_INDEX_NAME)
        print(f"Pineconeインデックス '{PINECONE_INDEX_NAME}' に接続しました")
        
        return _pinecone_index
    
    except Exception as e:
        print(f"Pinecone初期化エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

def add_skill_to_pinecone(skill_id, skill_name, user_id=None, user_name=None):
    """スキル情報をPineconeに追加"""
    try:
        index = get_pinecone_client()
        
        # メタデータを作成
        metadata = {
            "skill_id": skill_id,
            "skill_name": skill_name,
        }
        
        # ユーザー情報がある場合は追加
        if user_id is not None and user_name is not None:
            metadata["user_id"] = user_id
            metadata["user_name"] = user_name
            vector_id = f"skill_{skill_id}_user_{user_id}"
        else:
            vector_id = f"skill_{skill_id}"
        
        # OpenAIでテキストをベクトル化
        embedding = get_text_embedding(skill_name)
        
        # Pineconeにベクトルを追加（新APIバージョン）
        index.upsert(
            vectors=[{
                "id": vector_id,
                "values": embedding,
                "metadata": metadata
            }]
        )
        
        print(f"スキル '{skill_name}' (ID: {skill_id}) をPineconeに追加しました。")
        return True
    except Exception as e:
        print(f"スキル追加エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def search_similar_skills(query, limit=5):
    """Pineconeを使用して類似したスキルを検索"""
    try:
        index = get_pinecone_client()
        
        # クエリテキストをベクトル化
        query_embedding = get_text_embedding(query)
        
        # 類似検索を実行（新APIバージョン）
        results = index.query(
            vector=query_embedding,
            top_k=limit,
            include_metadata=True
        )
        
        # 結果をフォーマット（新APIバージョン）
        formatted_results = []
        for match in results.matches:
            formatted_results.append({
                "skill_id": match.metadata.get("skill_id"),
                "skill_name": match.metadata.get("skill_name"),
                "user_id": match.metadata.get("user_id"),
                "user_name": match.metadata.get("user_name"),
                "text": match.metadata.get("skill_name", ""),
                "score": match.score
            })
        
        return formatted_results
    
    except Exception as e:
        print(f"検索エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return [] 