from pathlib import Path
from datetime import datetime
import uuid
import json

from weasyprint import HTML

from app.config import get_settings
from app.services.llm_service import get_llm

settings = get_settings()


def generate_resume_html_directly(
    user_data: dict,
    job_title: str,
    company: str | None,
    job_description: str,
    style_description: str | None = None
) -> str:
    """
    一次调用大模型，直接生成完整可渲染的 HTML 简历
    """
    llm = get_llm()

    if style_description:
        style_prompt = f"\n风格要求：{style_description}（请严格遵循这个视觉风格来设计排版和配色）"
    else:
        style_prompt = "\n风格要求：现代、专业、简洁，使用蓝色系作为点缀色，适合互联网和技术岗位。"

    prompt = f"""你是专业的简历设计师和优化专家。请根据用户资料和目标岗位，直接生成一份完整、精美的 HTML 简历。

目标岗位：{job_title}
公司：{company or "未指定"}
岗位要求：
{job_description}

用户已有资料：
{json.dumps(user_data, ensure_ascii=False, indent=2)}
{style_prompt}

硬性要求：
1. 必须返回完整的 HTML 文档，包含 <!DOCTYPE html>、<html>、<head>、<style>、<body>
2. 必须使用 @page {{ size: A4; margin: 1.5cm 1.8cm; }} 设置纸张和边距
3. 必须包含以下部分（用户资料中有的信息一定要写进去，不要只写总结）：
   - 姓名 + 联系方式（顶部）
   - 个人总结（针对岗位优化，3-5句）
   - 工作经历（公司、职位、时间、要点列表）
   - 项目经历（项目名、时间、描述、亮点）
   - 教育背景
   - 专业技能
4. 只使用用户提供的真实信息，可以优化措辞和突出量化结果，严禁编造不存在的公司、项目、学校
5. 只返回纯 HTML 代码，不要任何解释，不要 markdown，不要 ```html 包裹

现在直接输出完整 HTML：
"""

    response = llm.invoke(prompt)
    content = response.content.strip()

    # 清理可能的 markdown 代码块
    if content.startswith("```"):
        lines = content.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines).strip()
        if content.lower().startswith("html"):
            content = content[4:].lstrip()

    return content.strip()


def generate_resume_pdf_from_html(html_content: str, user_id: int) -> str:
    """把 HTML 转成 PDF 并保存"""
    output_dir = Path(settings.GENERATED_DIR) / str(user_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"resume_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.pdf"
    pdf_path = output_dir / filename

    HTML(string=html_content).write_pdf(str(pdf_path))
    return str(pdf_path)


# 保留一个简单的风格模板生成函数（备用）
def generate_html_template_by_style(style_description: str) -> str:
    """根据风格描述生成 HTML 模板（备用，当前主流程已不需要）"""
    llm = get_llm()
    prompt = f"""你是专业的简历视觉设计师。请根据以下风格要求生成一个完整的 HTML+CSS 简历模板。

风格要求：{style_description}

要求：
1. 返回完整 HTML 文档
2. 使用 Jinja2 变量：{{{{ name }}}}、{{{{ contact }}}}、{{{{ summary }}}}、{{{{ work_experience }}}}、{{{{ projects }}}}、{{{{ education }}}}、{{{{ skills }}}}
3. 使用 @page 设置 A4
4. 只返回纯 HTML，不要解释

直接输出 HTML：
"""
    response = llm.invoke(prompt)
    content = response.content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines)
    return content.strip()