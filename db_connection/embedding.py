import os
import numpy as np
import openai
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL")

def get_text_embedding(text):
    """テキストからエンベディングを生成する"""
    print(f"エンベディング生成開始: {text}")
    
    if not text:
        print("エラー: テキストが空です")
        return None
        
    if not openai.api_key:
        print("エラー: OpenAI APIキーが設定されていません")
        return None
    
    if not OPENAI_MODEL:
        print("エラー: OpenAIモデルが設定されていません")
        return None
        
    try:
        print(f"OpenAI APIリクエスト送信: モデル={OPENAI_MODEL}")
        response = openai.embeddings.create(
            model=OPENAI_MODEL,
            input=text
        )
        print("OpenAI APIレスポンス受信")

        # レスポンスからエンベディングを取得
        embedding = response.data[0].embedding
        print(f"エンベディング生成成功: 次元数={len(embedding)}")
        return embedding
    
    except Exception as e:
        print(f"エンベディング生成エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def cosine_similarity(embedding1, embedding2):
    """2つのエンベディング間のコサイン類似度を計算する"""
    if embedding1 is None or embedding2 is None:
        print("エラー: エンベディングがNoneです")
        return 0
        
    embedding1 = np.array(embedding1)
    embedding2 = np.array(embedding2)

    # ベクトルのノルム（長さ）を計算
    norm1 = np.linalg.norm(embedding1)
    norm2 = np.linalg.norm(embedding2)
    
    # ゼロベクトルのチェック
    if norm1 == 0 or norm2 == 0:
        print("警告: ゼロベクトルが検出されました")
        return 0
    
    # コサイン類似度の計算
    similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
    print(f"コサイン類似度: {similarity}")
    return similarity