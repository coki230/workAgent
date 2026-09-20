# models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.model.base import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(100), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    resumes = relationship("Resume", back_populates="user")
    projects = relationship("Project", back_populates="user")
    job_applications = relationship("JobApplication", back_populates="user")


class Resume(Base):
    __tablename__ = "resumes"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    original_filename = Column(String(255))
    file_path = Column(String(500))  # 原始 PDF 路径
    raw_text = Column(Text)  # 完整提取文本
    structured_data = Column(JSON)  # 结构化后的 JSON
    source_type = Column(String(50))  # "pdf" / "manual" / "gitHub"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="resumes")


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    name = Column(String(200))
    github_url = Column(String(500))
    description = Column(Text)
    languages = Column(JSON)  # ["Python", "JS"]
    readme_content = Column(Text)
    stars = Column(Integer)
    extra_info = Column(JSON)  # 用户补充
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="projects")


class JobApplication(Base):
    __tablename__ = "job_applications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    job_title = Column(String(200))
    company = Column(String(200))
    job_description = Column(Text)
    structured_jd = Column(JSON)  # 解析后的 JD
    generated_resume = Column(JSON)  # 生成的结构化简历
    generated_file_path = Column(String(500))  # 最终 PDF/DOCX 路径
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="job_applications")