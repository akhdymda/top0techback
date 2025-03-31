from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import json
from typing import List #仮データ用
# from db_control import crud, mymodels
# from db_control import crud, mymodels
# # MySQLのテーブル作成　★コメントアウトされていたので外した（20250323）
# from db_control.create_tables_MySQL import init_db #★db_control.create_tables_MySQLに変更

# # # アプリケーション初期化時にテーブルを作成　★コメントアウトされていたので外した（20250323）
# init_db()


# class Customer(BaseModel):
#     customer_id: str
#     customer_name: str
#     age: int
#     gender: str


app = FastAPI()

# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
class User(BaseModel):
    id: int
    name: str
    department: str
    yearsOfService: int
    skills: List[str]
    description: str

def get_users_from_db() -> List[User]:
    return [
        User(
            id=1,
            name="高橋健人",
            department="リビング電気部",
            yearsOfService=13,
            skills=["Webマーケティング全般", "データ分析と計測", "コンテンツマーケティング", "SNSマーケティング"],
            description="経験豊富で技術にも強いマーケターです。"
        ),
        User(
            id=2,
            name="佐藤美咲",
            department="企画部",
            yearsOfService=8,
            skills=["新規事業企画", "社内プレゼン", "市場調査"],
            description="企画力と調整力に優れたリーダー型社員です。"
        ),
        User(
            id=3,
            name="田中陽介",
            department="エネルギー事業革新部",
            yearsOfService=5,
            skills=["IoT", "電力管理", "スマートホーム"],
            description="最新技術に強く、若手ながらも信頼される技術者です。"
        ),
        User(
            id=4,
            name="中村翔太",
            department="WEBソリューションプロジェクト部",
            yearsOfService=10,
            skills=["Web開発", "UI/UX設計", "SEO"],
            description="ユーザー視点でサービス設計を行うWeb系エンジニアです。"
        ),
    ]

#仮スキルDB
class Skill(BaseModel):
    name: str
    users: List[User] = []

def get_skills_from_db() -> List[Skill]:
    all_users = get_users_from_db()
    skills = [
        Skill(name="Webマーケティング全般"),
        Skill(name="SEO（検索エンジン最適化）"),
        Skill(name="コンテンツマーケティング"),
        Skill(name="SNSマーケティング"),
        Skill(name="広告運用（PPC・リスティング）"),
        Skill(name="メールマーケティング"),
        Skill(name="マーケティングオートメーション（MA）"),
        Skill(name="データ分析と計測"),
        Skill(name="グロースハック"),
        Skill(name="Eコマース・D2Cマーケティング"),
        Skill(name="AI・最新テクノロジーの活用")
    ]
    
    # 各スキルを持つユーザーを設定
    for skill in skills:
        skill.users = [user for user in all_users if skill.name in user.skills]
    
    return skills

#仮部署DB
class Department(BaseModel):
    name: str
    users: List[User] = []  # ユーザー情報を含めるように修正

def get_departments_from_db() -> List[Department]:
    all_users = get_users_from_db()
    departments = [
        Department(name="企画部"),
        Department(name="設備ソリューション事業部"),
        Department(name="リビング相談部"),
        Department(name="総合設備事業部"),
        Department(name="リビング営業部"),
        Department(name="BTMソリューションプロジェクト部"),
        Department(name="エネルギー事業革新部"),
        Department(name="WEBソリューションプロジェクト部"),
        Department(name="リビング業務改革部"),
        Department(name="ソリューション共創本部"),
    ]
    
    # 各部署に所属するユーザーを設定
    for dept in departments:
        dept.users = [user for user in all_users if user.department == dept.name]
    
    return departments


#ふわっと検索API
@app.get("/search", response_model=List[User])
def search_users(q: str = Query(..., min_length=1)):
    print(f"🔍 受け取ったクエリ: {q}", flush=True)

    
    return get_users_from_db()

#スキル検索API
@app.get("/skills/{skill_name}", response_model=Skill)
def read_skill(skill_name: str):
    skills = get_skills_from_db()
    for skill in skills:
        if skill.name == skill_name:
            return skill
    raise HTTPException(status_code=404, detail="Skill not found")

@app.get("/skills", response_model=List[Skill])
def read_skills():
    return get_skills_from_db()


#部署検索API
@app.get("/departments/{department_name}", response_model=Department)
def read_department(department_name: str):
    departments = get_departments_from_db()
    for dept in departments:
        if dept.name == department_name:
            return dept
    raise HTTPException(status_code=404, detail="Department not found")

@app.get("/departments", response_model=List[Department])
def read_departments():
    return get_departments_from_db()