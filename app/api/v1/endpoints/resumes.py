from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.model.models import Resume, User
from app.schema.schemas import ResumeOut
from app.services.resume_parser import extract_text_from_pdf, structure_resume_with_llm
from app.session import get_db
from app.utils.deps import get_current_user_id, get_or_create_user
from app.utils.file import save_upload_file

router = APIRouter()

@router.post("/upload", response_model=ResumeOut)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "只支持 PDF 文件")

    get_or_create_user(current_user.id, db)

    content = await file.read()
    file_path = save_upload_file(current_user.id, file.filename, content)

    raw_text = extract_text_from_pdf(file_path)
    structured = structure_resume_with_llm(raw_text)

    resume = Resume(
        user_id=current_user.id,
        original_filename=file.filename,
        file_path=file_path,
        raw_text=raw_text,
        structured_data=structured,
        source_type="pdf"
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume

@router.get("/", response_model=list[ResumeOut])
def list_resumes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(Resume).filter(Resume.user_id == current_user.id).order_by(Resume.created_at.desc()).all()


class SupplementRequest(BaseModel):
    content: str


@router.post("/supplement")
def save_supplement(
        body: SupplementRequest,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """保存用户随时发送的补充信息"""
    # 简单做法：追加到最新的一份 Resume 的 structured_data 里
    # 更好的做法是单独建一张 Supplement 表，这里先用简单方式

    resume = db.query(Resume).filter(Resume.user_id == current_user.id) \
        .order_by(Resume.created_at.desc()).first()

    if not resume:
        # 如果还没有简历，就创建一条纯文字记录
        resume = Resume(
            user_id=current_user.id,
            original_filename="supplement.txt",
            source_type="manual",
            raw_text=body.content,
            structured_data={"supplements": [body.content]}
        )
        db.add(resume)
    else:
        data = resume.structured_data or {}
        if "supplements" not in data:
            data["supplements"] = []
        data["supplements"].append(body.content)
        resume.structured_data = data
        resume.raw_text = (resume.raw_text or "") + "\n\n" + body.content

    db.commit()
    return {"message": "已保存", "content": body.content}