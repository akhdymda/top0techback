import os
import numpy as np
import openai
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL")

def get_text_embedding(text):
    """テキストからエンベディングを生成する"""

    if not openai.api_key:
        raise ValueError("OpenAI APIキーが設定されていません。")
    
    try:
        response = openai.embeddings.create(
            model=OPENAI_MODEL,
            input=text
        )

        # レスポンスからエンベディングを取得
        embedding = response.data[0].embedding

        return embedding
    
    except Exception as e:
        print(f"エンベディング生成リクエストエラー: {e}")
        raise

def cosine_similarity(embedding1, embedding2):
    """2つのエンベディング間のコサイン類似度を計算する"""
    embedding1 = np.array(embedding1)
    embedding2 = np.array(embedding2)

    # ベクトルのノルム（長さ）を計算
    norm1 = np.linalg.norm(embedding1)
    norm2 = np.linalg.norm(embedding2)
    
    # ゼロベクトルのチェック
    if norm1 == 0 or norm2 == 0:
        return 0
    
    # コサイン類似度の計算
    return np.dot(embedding1, embedding2) / (norm1 * norm2)