from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import json

from app.api.deps import get_current_user
from app.model.models import User, Resume, Project, JobApplication
from app.schema.schemas import GenerateRequest
from app.services.llm_service import get_llm
from app.services.pdf_generator import generate_resume_pdf, generate_html_template_by_style
from app.session import get_db

router = APIRouter()

@router.post("/")
def generate_resume(
    body: GenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ========== 1. 更完整地聚合用户所有数据 ==========
    resumes = db.query(Resume).filter(Resume.user_id == current_user.id)\
                .order_by(Resume.created_at.desc()).all()
    projects = db.query(Project).filter(Project.user_id == current_user.id).all()

    # 合并所有简历的结构化数据 + 补充信息
    all_structured = []
    all_raw_text = []
    all_supplements = []

    for r in resumes:
        if r.structured_data:
            all_structured.append(r.structured_data)
        if r.raw_text:
            all_raw_text.append(r.raw_text)
        if r.structured_data and "supplements" in r.structured_data:
            all_supplements.extend(r.structured_data["supplements"])

    user_data = {
        "structured_resumes": all_structured,
        "raw_texts": all_raw_text[:3],          # 防止太长
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

    # ========== 2. 更强制的 Prompt ==========
    llm = get_llm()
    prompt = f"""你是资深简历优化专家。必须根据用户提供的全部资料，生成一份完整、真实的简历。

目标岗位：{body.job_title}
公司：{body.company or "未指定"}
岗位要求：
{body.job_description}

用户已有全部资料（请充分利用，不要忽略）：
{json.dumps(user_data, ensure_ascii=False, indent=2)}

【重要强制要求】
1. 必须返回完整的 JSON，包含以下所有字段，一个都不能少：
   - name
   - contact
   - summary
   - work_experience（数组，至少尝试提取或整理出工作经历）
   - projects（数组）
   - education（数组）
   - skills（数组）
2. 如果用户资料中有工作经历、项目、教育、技能，必须全部整理进去，禁止只返回 summary。
3. 只使用用户提供的真实信息，可以优化表达和量化，但禁止编造不存在的公司、项目、学校。
4. highlights 尽量写成有结果的点（数字、成果、技术栈）。
5. 只返回合法 JSON，不要 markdown，不要解释，不要代码块。

JSON 格式严格如下：
{{
  "name": "姓名",
  "contact": "电话 | 邮箱 | 城市",
  "summary": "3-5句针对性总结",
  "work_experience": [
    {{
      "company": "公司名",
      "title": "职位",
      "period": "2021.03 - 2024.06",
      "highlights": ["成果1", "成果2"]
    }}
  ],
  "projects": [
    {{
      "name": "项目名",
      "period": "2023.01 - 2023.08",
      "description": "一句话描述",
      "highlights": ["亮点1", "亮点2"]
    }}
  ],
  "education": [
    {{
      "school": "学校",
      "degree": "学历 + 专业",
      "period": "2017 - 2021"
    }}
  ],
  "skills": ["Python", "FastAPI", "MySQL"]
}}
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
        resume_data = json.loads(content)
    except json.JSONDecodeError as e:
        return {
            "error": "大模型返回的 JSON 解析失败",
            "raw": content,
            "parse_error": str(e)
        }

    # 安全检查：如果关键字段缺失，给出提示
    required_fields = ["name", "summary", "work_experience", "projects", "education", "skills"]
    missing = [f for f in required_fields if f not in resume_data]
    if missing:
        return {
            "error": f"生成结果缺少字段: {missing}",
            "raw_data": resume_data
        }

    # ========== 3. 生成 PDF ==========
    custom_html = None
    if body.style_description:
        custom_html = generate_html_template_by_style(body.style_description)

    pdf_path = generate_resume_pdf(
        data=resume_data,
        user_id=current_user.id,
        template_name=body.template_name or "modern",
        custom_html=custom_html
    )

    # 保存记录
    app = JobApplication(
        user_id=current_user.id,
        job_title=body.job_title,
        company=body.company,
        job_description=body.job_description,
        generated_resume=resume_data,
        generated_file_path=pdf_path,
        status="completed"
    )
    db.add(app)
    db.commit()
    db.refresh(app)

    return {
        "application_id": app.id,
        "pdf_url": f"/api/v1/generate/download/{app.id}",
        "message": "简历 PDF 已生成",
        "debug_data": resume_data          # 临时加上，方便你看生成了什么
    }

@router.get("/download/{application_id}")
def download_resume(
        application_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    app = db.query(JobApplication).filter(
        JobApplication.id == application_id,
        JobApplication.user_id == current_user.id
    ).first()

    if not app or not app.generated_file_path:
        from fastapi import HTTPException
        raise HTTPException(404, "文件不存在")

    return FileResponse(
        path=app.generated_file_path,
        filename=f"简历_{app.job_title}.pdf",
        media_type="application/pdf"
    )