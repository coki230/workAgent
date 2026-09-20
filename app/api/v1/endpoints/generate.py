from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import json

from app.api.deps import get_current_user
from app.model.models import Resume, Project, JobApplication, User
from app.schema.schemas import GenerateRequest
from app.services.llm_service import get_llm
from app.session import get_db

router = APIRouter()

@router.post("/")
def generate_resume(
    body: GenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    resume = db.query(Resume).filter(Resume.user_id == current_user.id).order_by(Resume.created_at.desc()).first()
    projects = db.query(Project).filter(Project.user_id == current_user.id).all()

    user_data = {
        "resume": resume.structured_data if resume else {},
        "projects": [
            {
                "name": p.name,
                "description": p.description,
                "languages": p.languages,
                "stars": p.stars,
                "url": p.github_url
            } for p in projects
        ]
    }

    llm = get_llm()
    prompt = f"""你是专业的简历优化专家。请根据以下用户资料和职位要求，生成一份高度匹配的简历（JSON 格式）。

职位：{body.job_title}
公司：{body.company or "未知"}
职位要求：
{body.job_description}

用户资料：
{json.dumps(user_data, ensure_ascii=False, indent=2)}

请只返回合法 JSON，包含：summary, work_experience, projects, skills 等字段。
"""
    response = llm.invoke(prompt)
    generated = response.content

    app = JobApplication(
        user_id=current_user.id,
        job_title=body.job_title,
        company=body.company,
        job_description=body.job_description,
        generated_resume={"raw": generated},
        status="completed"
    )
    db.add(app)
    db.commit()
    db.refresh(app)

    return {
        "application_id": app.id,
        "generated_resume": generated
    }