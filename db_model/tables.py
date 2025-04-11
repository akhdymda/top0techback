from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey, UniqueConstraint, LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db_connection.connect_MySQL import Base

class User(Base):
    """ユーザーテーブル (Userマスタ)"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # リレーションシップ
    profile = relationship("Profile", back_populates="user", uselist=False)
    posted_skills = relationship("PostSkill", back_populates="user")
    contacts = relationship("PostContact", back_populates="user")
    sent_thanks = relationship("Thanks", foreign_keys="Thanks.giver_user_id", back_populates="giver")
    received_thanks = relationship("Thanks", foreign_keys="Thanks.receiver_user_id", back_populates="receiver")
    bookmarks_made = relationship("Bookmark", foreign_keys="Bookmark.bookmarking_user_id", back_populates="bookmarker")
    bookmarks_received = relationship("Bookmark", foreign_keys="Bookmark.bookmarked_user_id", back_populates="bookmarked")

class Department(Base):
    """部署マスタ (Departmentマスタ)"""
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)

    # リレーションシップ
    profiles = relationship("Profile", back_populates="department")

class JoinForm(Base):
    """入社形態マスタ (join_formマスタ)"""
    __tablename__ = "join_forms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)

    # リレーションシップ
    profiles = relationship("Profile", back_populates="join_form")

class WelcomeLevel(Base):
    """歓迎度マスタ (welcome level)"""
    __tablename__ = "welcome_levels"

    id = Column(Integer, primary_key=True, index=True)
    level_name = Column(String(100), nullable=False)

    # リレーションシップ
    profiles = relationship("Profile", back_populates="welcome_level")

class SkillMaster(Base):
    """スキルマスタ (skillマスタ)"""
    __tablename__ = "skill_masters"
    
    skill_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # リレーションシップ
    post_skills = relationship("PostSkill", back_populates="skill")
    detail_skills = relationship("DetailSkill", back_populates="skill")

class DetailSkill(Base):
    """詳細スキルマスタ (dskillマスタ)"""
    __tablename__ = "detail_skills"

    dskill_id = Column(Integer, primary_key=True, index=True)
    dskill_name = Column(String(100), nullable=False)
    skill_id = Column(Integer, ForeignKey("skill_masters.skill_id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # リレーションシップ
    skill = relationship("SkillMaster", back_populates="detail_skills")

class ContactMethod(Base):
    """連絡方法マスタ (contactマスタ)"""
    __tablename__ = "contact_methods"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)

    # リレーションシップ
    post_contacts = relationship("PostContact", back_populates="contact_method")

class Profile(Base):
    """プロフィールテーブル (profile)"""
    __tablename__ = "profiles"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    join_form_id = Column(Integer, ForeignKey("join_forms.id"), nullable=True)
    welcome_level_id = Column(Integer, ForeignKey("welcome_levels.id"), nullable=True)
    career = Column(Integer, nullable=True) # 社歴
    image_data = Column(LargeBinary, nullable=True) # プロフィール画像データ
    image_data_type = Column(String(100), nullable=True) # プロフィール画像データの形式
    history = Column(Text, nullable=True) # 経歴
    pr = Column(Text, nullable=True) # 自己PR
    total_point = Column(Integer, default=0) # 付与ポイント数合計
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # リレーションシップ
    user = relationship("User", back_populates="profile")
    department = relationship("Department", back_populates="profiles")
    join_form = relationship("JoinForm", back_populates="profiles")
    welcome_level = relationship("WelcomeLevel", back_populates="profiles")

class PostSkill(Base):
    """ユーザースキルテーブル (Post skillマスタ)"""
    __tablename__ = "post_skills"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    skill_id = Column(Integer, ForeignKey("skill_masters.skill_id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # ユニーク制約
    __table_args__ = (
        UniqueConstraint('user_id', 'skill_id', name='unique_user_skill'),
    )

    # リレーションシップ
    user = relationship("User", back_populates="posted_skills")
    skill = relationship("SkillMaster", back_populates="post_skills")

class PostContact(Base):
    """ユーザー連絡先テーブル (Post contactマスタ)"""
    __tablename__ = "post_contacts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    contact_id = Column(Integer, ForeignKey("contact_methods.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # ユニーク制約
    __table_args__ = (
        UniqueConstraint('user_id', 'contact_id', name='unique_user_contact'),
    )

    # リレーションシップ
    user = relationship("User", back_populates="contacts")
    contact_method = relationship("ContactMethod", back_populates="post_contacts")

class Thanks(Base):
    """サンクスポイントテーブル (thanks_point)"""
    __tablename__ = "thanks"

    id = Column(Integer, primary_key=True, index=True)
    give_date = Column(Date, nullable=False, default=func.current_date())
    giver_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    receiver_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    points = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    # リレーションシップ
    giver = relationship("User", foreign_keys=[giver_user_id], back_populates="sent_thanks")
    receiver = relationship("User", foreign_keys=[receiver_user_id], back_populates="received_thanks")

class Bookmark(Base):
    """ブックマークテーブル (bookmarkテーブル)"""
    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True, index=True)
    bookmark_date = Column(Date, nullable=False, default=func.current_date())
    bookmarking_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    bookmarked_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    # ユニーク制約
    __table_args__ = (
        UniqueConstraint('bookmarking_user_id', 'bookmarked_user_id', name='unique_bookmark'),
    )

    # リレーションシップ
    bookmarker = relationship("User", foreign_keys=[bookmarking_user_id], back_populates="bookmarks_made")
    bookmarked = relationship("User", foreign_keys=[bookmarked_user_id], back_populates="bookmarks_received")