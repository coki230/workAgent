from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
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