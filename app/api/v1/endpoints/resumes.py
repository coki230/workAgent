import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.model.models import Resume, User, Project
from app.schema.schemas import ResumeOut
from app.services.llm_service import get_llm
from app.services.resume_parser import extract_text_from_pdf, structure_resume_with_llm
from app.session import get_db
from app.utils.deps import get_or_create_user
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

class AnalyzeResponse(BaseModel):
    summary: str
    conflicts: List[str]
    optimizations: List[str]
    suggestions: List[str]
    raw_analysis: Optional[str] = None

@router.post("/analyze", response_model=AnalyzeResponse, summary="简历体检")
def analyze_resume(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    自动分析当前用户已保存的所有内容，找出逻辑冲突和可优化点
    """
    # 聚合用户数据（与生成简历时保持一致）
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
        if r.structured_data and isinstance(r.structured_data, dict) and "supplements" in r.structured_data:
            all_supplements.extend(r.structured_data["supplements"])

    user_data = {
        "structured_resumes": all_structured,
        "raw_texts": all_raw_text[:3],
        "supplements": all_supplements,
        "github_projects": [
            {
                "name": p.name,
                "description": p.description,
                "languages": p.languages,
                "stars": p.stars,
                "url": p.github_url
            } for p in projects
        ]
    }

    if not any([all_structured, all_raw_text, all_supplements, projects]):
        return AnalyzeResponse(
            summary="目前还没有检测到任何已保存的内容，请先上传简历或补充信息。",
            conflicts=[],
            optimizations=[],
            suggestions=[]
        )

    llm = get_llm()
    prompt = f"""你是一位严谨的简历审阅专家。请对用户已保存的全部内容进行「体检」，找出问题并给出可执行的优化建议。

用户全部资料：
{json.dumps(user_data, ensure_ascii=False, indent=2)}

请从以下几个维度分析：
1. 逻辑冲突 / 不一致的地方（时间重叠、公司/职位矛盾、技能与经历不匹配、前后描述冲突等）
2. 可以优化的地方（量化不足、表述空泛、重点不突出、缺少成果、结构混乱等）
3. 具体可执行的修改建议

输出要求（必须严格返回 JSON）：
{{
  "summary": "一句话总结整体情况",
  "conflicts": ["冲突点1", "冲突点2"],
  "optimizations": ["可优化点1", "可优化点2"],
  "suggestions": ["具体建议1（说明为什么以及如何改）", "具体建议2"]
}}

注意：
- 只基于用户真实内容分析，不要编造
- 建议要具体、可操作
- 只返回合法 JSON，不要解释，不要 markdown
"""

    response = llm.invoke(prompt)
    content = response.content.strip()

    # 清理代码块
    if "```" in content:
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    content = content.strip()

    try:
        result = json.loads(content)
        return AnalyzeResponse(
            summary=result.get("summary", ""),
            conflicts=result.get("conflicts", []),
            optimizations=result.get("optimizations", []),
            suggestions=result.get("suggestions", []),
            raw_analysis=content
        )
    except Exception as e:
        return AnalyzeResponse(
            summary="分析过程出现解析问题，请稍后重试。",
            conflicts=[],
            optimizations=[],
            suggestions=[],
            raw_analysis=content
        )

class ApplyOptimizationRequest(BaseModel):
    instruction: str = Field(..., description="用户的确认指令，例如：按建议全部修改 / 只改第2、3点")
    previous_analysis: Optional[dict] = None   # 可选，前端可把上次体检结果传回来


class ApplyOptimizationResponse(BaseModel):
    message: str
    optimized_data: Optional[dict] = None
    resume_id: Optional[int] = None


@router.post("/apply-optimization", response_model=ApplyOptimizationResponse, summary="应用体检优化建议")
def apply_optimization(
    body: ApplyOptimizationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    根据用户确认指令，对已保存内容进行优化，并写回数据库
    """
    # ---------- 1. 聚合当前用户所有数据 ----------
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
        if r.structured_data and isinstance(r.structured_data, dict) and "supplements" in r.structured_data:
            all_supplements.extend(r.structured_data["supplements"])

    if not any([all_structured, all_raw_text, all_supplements, projects]):
        return ApplyOptimizationResponse(
            message="当前没有可优化的内容，请先上传简历或补充信息。"
        )

    user_data = {
        "structured_resumes": all_structured,
        "raw_texts": all_raw_text[:3],
        "supplements": all_supplements,
        "github_projects": [
            {
                "name": p.name,
                "description": p.description,
                "languages": p.languages,
                "stars": p.stars,
                "url": p.github_url
            } for p in projects
        ]
    }

    # ---------- 2. 让大模型根据「原数据 + 用户指令」生成优化后的结构化简历 ----------
    llm = get_llm()

    analysis_part = ""
    if body.previous_analysis:
        analysis_part = f"\n上次体检结果：\n{json.dumps(body.previous_analysis, ensure_ascii=False, indent=2)}\n"

    prompt = f"""你是专业的简历优化专家。请根据用户的原始资料和确认指令，生成一份优化后的结构化简历。

用户确认指令：{body.instruction}
{analysis_part}

用户原始资料：
{json.dumps(user_data, ensure_ascii=False, indent=2)}

优化要求：
1. 严格遵循用户的确认指令（全部修改 / 只改某几点）
2. 只使用用户已有真实信息，禁止编造公司、项目、学校、时间
3. 重点解决逻辑冲突、补充量化、优化表述、让重点更突出
4. 返回完整的结构化 JSON，格式如下：

{{
  "personal_info": {{
    "name": "",
    "email": "",
    "phone": "",
    "location": ""
  }},
  "summary": "优化后的个人总结",
  "education": [
    {{
      "school": "",
      "degree": "",
      "period": ""
    }}
  ],
  "work_experience": [
    {{
      "company": "",
      "title": "",
      "period": "",
      "highlights": ["优化后的要点1", "要点2"]
    }}
  ],
  "projects": [
    {{
      "name": "",
      "period": "",
      "description": "",
      "highlights": ["亮点1", "亮点2"]
    }}
  ],
  "skills": ["技能1", "技能2"],
  "certificates": [],
  "others": "",
  "optimization_note": "本次主要做了哪些优化（简要说明）"
}}

只返回合法 JSON，不要解释，不要 markdown。
"""

    response = llm.invoke(prompt)
    content = response.content.strip()

    # 清理代码块
    if "```" in content:
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    content = content.strip()

    try:
        optimized_data = json.loads(content)
    except Exception as e:
        return ApplyOptimizationResponse(
            message=f"优化结果解析失败，请重试。错误：{str(e)}"
        )

    # ---------- 3. 写回数据库（新增一条优化后的记录） ----------
    new_resume = Resume(
        user_id=current_user.id,
        original_filename="optimized_by_checkup.json",
        file_path="",
        raw_text=json.dumps(optimized_data, ensure_ascii=False, indent=2),
        structured_data=optimized_data,
        source_type="optimized",          # 标记为优化版本
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(new_resume)
    db.commit()
    db.refresh(new_resume)

    note = optimized_data.get("optimization_note", "已根据你的确认完成优化")

    return ApplyOptimizationResponse(
        message=f"已根据你的指令完成优化并保存！\n优化说明：{note}",
        optimized_data=optimized_data,
        resume_id=new_resume.id
    )