from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date

# ユーザー関連スキーマ
class UserBase(BaseModel):
    name: Optional[str] = None
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    name: str
    department: str
    yearsOfService: int
    skills: List[str]
    description: str
    joinForm: str  # 入社形態を追加
    class Config:
        from_attributes = True


    class Config:
        orm_mode = True

# 部署関連スキーマ
class DepartmentBase(BaseModel):
    name: str

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentResponse(DepartmentBase):
    name: str
    users: List[UserResponse] = []

    class Config:
        from_attributes = True

# 入社形態関連スキーマ
class JoinFormBase(BaseModel):
    name: str

class JoinFormCreate(JoinFormBase):
    pass

class JoinFormResponse(JoinFormBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

# 歓迎度関連スキーマ
class WelcomeLevelBase(BaseModel):
    level_name: str

class WelcomeLevelCreate(WelcomeLevelBase):
    pass

class WelcomeLevelResponse(WelcomeLevelBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

# スキルマスター関連スキーマ
class SkillMasterBase(BaseModel):
    name: str

class SkillMasterCreate(SkillMasterBase):
    pass

class SkillMasterResponse(SkillMasterBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

class SkillResponse(BaseModel):
    name: str
    users: List[UserResponse] = []
    class Config:
        from_attributes = True

# 詳細スキル関連スキーマ
class DetailSkillBase(BaseModel):
    name: str
    skill_id: Optional[int] = None

class DetailSkillCreate(DetailSkillBase):
    pass

class DetailSkillResponse(DetailSkillBase):
    id: int

    class Config:
        orm_mode = True

# 連絡方法関連スキーマ
class ContactMethodBase(BaseModel):
    name: str

class ContactMethodCreate(ContactMethodBase):
    pass

class ContactMethodResponse(ContactMethodBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

# プロフィール関連スキーマ
class ProfileBase(BaseModel):
    department_id: Optional[int] = None
    join_form_id: Optional[int] = None
    welcome_level_id: Optional[int] = None
    career: Optional[int] = None
    image_url: Optional[str] = None
    history: Optional[str] = None
    pr: Optional[str] = None
    total_point: int = 0

class ProfileCreate(ProfileBase):
    user_id: int

class ProfileUpdate(ProfileBase):
    pass

class ProfileResponse(ProfileBase):
    user_id: int
    created_at: datetime
    department: Optional[DepartmentResponse] = None
    join_form: Optional[JoinFormResponse] = None
    welcome_level: Optional[WelcomeLevelResponse] = None

    class Config:
        orm_mode = True

# ユーザースキル関連スキーマ
class PostSkillBase(BaseModel):
    user_id: int
    skill_id: int


class PostSkillCreate(PostSkillBase):
    pass

class PostSkillUpdate(BaseModel):
    description: Optional[str] = None

class PostSkillResponse(PostSkillBase):
    id: int
    created_at: datetime
    skill: Optional[SkillMasterResponse] = None

    class Config:
        orm_mode = True

# ユーザー連絡先関連スキーマ
class PostContactBase(BaseModel):
    user_id: int
    contact_id: int
    contact_value: Optional[str] = None

class PostContactCreate(PostContactBase):
    pass

class PostContactResponse(PostContactBase):
    id: int
    created_at: datetime
    contact_method: Optional[ContactMethodResponse] = None

    class Config:
        orm_mode = True

# サンクスポイント関連スキーマ
class ThanksBase(BaseModel):
    giver_user_id: int
    receiver_user_id: int
    points: int = Field(default=1, ge=1, le=5)
    message: Optional[str] = None

class ThanksCreate(ThanksBase):
    pass

class ThanksResponse(ThanksBase):
    id: int
    give_date: date
    created_at: datetime

    class Config:
        orm_mode = True

# ブックマーク関連スキーマ
class BookmarkBase(BaseModel):
    bookmarking_user_id: int
    bookmarked_user_id: int

class BookmarkCreate(BookmarkBase):
    pass

class BookmarkResponse(BookmarkBase):
    id: int
    bookmark_date: date
    created_at: datetime

    class Config:
        orm_mode = True

# 検索関連スキーマ
class SearchQuery(BaseModel):
    query: str
    limit: Optional[int] = 10

class SearchResult(BaseModel):
    user_id: int
    user_name: str
    skill_id: Optional[int] = None
    skill_name: Optional[str] = None
    joinForm: Optional[str] = None
    description: Optional[str] = None
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    similarity_score: float

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int 