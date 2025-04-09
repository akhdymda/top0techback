from db_connection.connect_Pinecone import get_pinecone_client

def check_pinecone_data():
    """Pineconeに格納されているデータを確認"""
    try:
        # Pineconeインデックスの取得
        index = get_pinecone_client()
        
        # インデックスの統計情報を取得
        stats = index.describe_index_stats()
        
        print(f"Pineconeインデックス情報:")
        print(f"- ベクトル数: {stats.total_vector_count}")
        print(f"- 次元数: {stats.dimension}")
        
        # データが存在しない場合
        if stats.total_vector_count == 0:
            print("Pineconeにデータが格納されていません。")
            return False
        else:
            print("Pineconeにデータが格納されています。")
            return True
            
    except Exception as e:
        print(f"Pineconeデータ確認エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_pinecone_data() 