import chromadb
from chromadb.config import Settings
from functools import lru_cache
import os
from pathlib import Path
from dotenv import load_dotenv

# 環境変数の読み込み
base_path = Path(__file__).parents[1]  # backendディレクトリへのパス
env_path = base_path / '.env'
load_dotenv(dotenv_path=env_path)

# ChromaDBクライアントのインスタンス
_chroma_client = None

@lru_cache
def get_chroma_client():
    """ChromaDBクライアントのシングルトンインスタンスを返す。キャッシュすることでアプリケーション全体で再利用できる"""
    global _chroma_client
    
    # 既にインスタンスがある場合はそれを返す
    if _chroma_client is not None:
        return _chroma_client
    
    try:
        # まずHTTPクライアントで接続を試みる
        host = os.getenv('CHROMA_HOST', 'localhost')
        port = int(os.getenv('CHROMA_PORT', '8080'))
        
        _chroma_client = chromadb.HttpClient(
            host=host,
            port=port
        )
        print("ChromaDB HTTPクライアントに接続しました")
    except Exception as e:
        print(f"HTTPクライアント接続エラー: {e}. フォールバックとしてPersistentClientを使用します")
        # 接続に失敗した場合はローカルの永続クライアントにフォールバック
        _chroma_client = chromadb.PersistentClient(
            path="chroma_db",
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=False
            )
        )
        print(f"ChromaDB PersistentClientを作成しました")

    return _chroma_client

def get_collection(collection_name="skills"):
    """指定されたコレクションを取得する。コレクションが存在しない場合は新しく作成する"""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"} #コサイン類似度を使用
    )

def add_embedding(id, embedding, metadata=None, text=None, collection_name="skills"):
    """ChromaDBにエンベディングを追加する"""
    collection = get_collection(collection_name)
    collection.add(
        ids=[str(id)],
        embeddings=[embedding],
        metadatas=[metadata] if metadata else None,
        documents=[text] if text else None
    )
    return True

def search_similar(embedding, limit=50, collection_name="skills"):
    """類似したエンベディングを検索する"""
    collection = get_collection(collection_name)
    print(f"コレクション '{collection_name}' で検索を実行")
    
    # コレクション内のドキュメント数を確認
    collection_count = collection.count()
    print(f"コレクション '{collection_name}' のドキュメント数: {collection_count}")
    
    if collection_count == 0:
        print(f"コレクション '{collection_name}' にはドキュメントが存在しません")
        return {"ids": [[]], "distances": [[]], "metadatas": [[]], "documents": [[]]}
    
    # 検索実行
    results = collection.query(
        query_embeddings=[embedding],
        n_results=min(limit, collection_count)  # コレクション内のドキュメント数を超えないように
    )
    
    print(f"検索結果: {len(results['ids'][0])}件")
    return results

def list_collection_items(collection_name="skills", limit=100):
    """コレクション内のアイテムを一覧取得する（デバッグ用）"""
    collection = get_collection(collection_name)
    count = collection.count()
    
    if count == 0:
        print(f"コレクション '{collection_name}' は空です")
        return None
    
    # すべてのアイテムを取得（最大limitまで）
    results = collection.get(limit=min(limit, count))
    print(f"コレクション '{collection_name}' のアイテム数: {count}件")
    return results
