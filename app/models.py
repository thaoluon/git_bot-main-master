from sqlalchemy import Column, Integer, String, Boolean, Text, UniqueConstraint
from .database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint('git_username', name='uq_user_git_username'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255))
    location = Column(String(255))
    email = Column(String(255), nullable=True)
    country = Column(String(10), nullable=True, index=True)  # ISO country code (e.g., 'PK', 'US', 'NO') or timezone offset (e.g., '+0300', '-0500')
    contacted = Column(Boolean, default=False)
    responded = Column(Boolean, default=False)
    git_username = Column(String(255), nullable=True, unique=True, index=True)


class FetchState(Base):
    __tablename__ = "fetch_state"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    key = Column(String(50), unique=True, nullable=False, default="github_since")
    since_value = Column(Integer, default=0)
