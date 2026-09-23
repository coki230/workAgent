from pydantic import BaseModel
from typing import Optional, Any, List
from datetime import datetime

class ResumeOut(BaseModel):
    id: int
    original_filename: Optional[str]
    source_type: str
    structured_data: Optional[Any]
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectCreate(BaseModel):
    github_username: Optional[str] = None
    github_url: Optional[str] = None
    extra_info: Optional[str] = None

class ProjectOut(BaseModel):
    id: int
    name: Optional[str]
    github_url: Optional[str]
    description: Optional[str]
    languages: Optional[List[str]]
    stars: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True

class GenerateRequest(BaseModel):
    job_title: str
    company: Optional[str] = None
    job_description: str
    template_name: Optional[str] = "modern"  # 内置模板名（备用）
    style_description: Optional[str] = None  # 新增：自然语言风格描述


