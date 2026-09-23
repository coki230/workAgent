from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.model.models import User, Resume, Project, JobApplication
from app.schema.schemas import GenerateRequest
from app.services.pdf_generator import generate_resume_html_directly, generate_resume_pdf_from_html
from app.session import get_db

router = APIRouter()


@router.post("/")
def generate_resume(
    body: GenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    根据用户已保存的所有资料 + 岗位要求，直接生成精美 PDF 简历
    """
    # 1. 聚合当前用户的所有历史数据
    resumes = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
        .all()
    )
    projects = (
        db.query(Project)
        .filter(Project.user_id == current_user.id)
        .all()
    )

    all_structured = []
    all_raw_text = []
    all_supplements = []

    for r in resumes:
        if r.structured_data:
            all_structured.append(r.structured_data)
        if r.raw_text:
            all_raw_text.append(r.raw_text)
        if (
            r.structured_data
            and isinstance(r.structured_data, dict)
            and "supplements" in r.structured_data
        ):
            all_supplements.extend(r.structured_data["supplements"])

    user_data = {
        "structured_resumes": all_structured,
        "raw_texts": all_raw_text[:2],  # 控制长度，防止 prompt 过长
        "supplements": all_supplements,
        "github_projects": [
            {
                "name": p.name,
                "description": p.description,
                "languages": p.languages,
                "stars": p.stars,
                "url": p.github_url,
            }
            for p in projects
        ],
    }

    # 2. 一次大模型调用，直接生成完整 HTML
    html_content = generate_resume_html_directly(
        user_data=user_data,
        job_title=body.job_title,
        company=body.company,
        job_description=body.job_description,
        style_description=body.style_description,
    )

    if not html_content or len(html_content) < 200:
        raise HTTPException(status_code=500, detail="大模型生成 HTML 失败，请重试")

    # 3. HTML → PDF
    pdf_path = generate_resume_pdf_from_html(html_content, current_user.id)

    # 4. 记录到数据库
    app = JobApplication(
        user_id=current_user.id,
        job_title=body.job_title,
        company=body.company,
        job_description=body.job_description,
        generated_resume={"preview": html_content[:800]},  # 只存预览，避免字段过长
        generated_file_path=pdf_path,
        status="completed",
    )
    db.add(app)
    db.commit()
    db.refresh(app)

    return {
        "application_id": app.id,
        "pdf_url": f"/api/v1/generate/download/{app.id}",
        "message": "简历 PDF 已生成成功",
    }


@router.get("/download/{application_id}")
def download_resume(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """下载生成的 PDF"""
    app = (
        db.query(JobApplication)
        .filter(
            JobApplication.id == application_id,
            JobApplication.user_id == current_user.id,
        )
        .first()
    )

    if not app or not app.generated_file_path:
        raise HTTPException(status_code=404, detail="文件不存在或已被删除")

    filename = f"简历_{app.job_title or 'resume'}.pdf"
    return FileResponse(
        path=app.generated_file_path,
        filename=filename,
        media_type="application/pdf",
    )