from pathlib import Path
from weasyprint import HTML
from jinja2 import Environment, FileSystemLoader, Template
import uuid
from datetime import datetime

from app.config import get_settings
from app.services.llm_service import get_llm

settings = get_settings()

# 内置模板目录（如果还没有可先忽略）
TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "templates" / "resume_styles"

def generate_html_template_by_style(style_description: str) -> str:
    """
    方案 C：根据用户描述的风格，让大模型生成完整的 HTML+CSS 模板
    """
    llm = get_llm()
    prompt = f"""你是一位专业的简历视觉设计师。请根据下面的风格要求，生成一个完整的、可直接使用的 HTML + CSS 简历模板。

风格要求：
{style_description}

硬性要求：
1. 必须返回完整的 HTML 文档，包含 <!DOCTYPE html>、<html>、<head>、<style>、<body>
2. 使用 Jinja2 语法，必须支持以下变量（不要改名字）：
   - {{{{ name }}}}
   - {{{{ contact }}}}
   - {{{{ summary }}}}
   - {{{{ work_experience }}}}   （列表，每项包含 company, title, period, highlights）
   - {{{{ projects }}}}          （列表，每项包含 name, period, description, highlights）
   - {{{{ education }}}}         （列表，每项包含 school, degree, period）
   - {{{{ skills }}}}            （字符串列表）
3. 必须使用 @page {{ size: A4; margin: ... }} 设置纸张
4. 只返回纯 HTML 代码，不要任何解释、不要 markdown 代码块、不要 ```html

现在请直接输出完整 HTML 模板：
"""
    response = llm.invoke(prompt)
    content = response.content.strip()

    # 清理可能的代码块包裹
    if content.startswith("```"):
        lines = content.split("\n")
        # 去掉第一行和最后一行的 ```
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines)
        if content.startswith("html"):
            content = content[4:].lstrip()

    return content.strip()


def generate_resume_pdf(
    data: dict,
    user_id: int,
    template_name: str = "modern",
    custom_html: str | None = None
) -> str:
    """
    生成 PDF
    - custom_html 优先级最高（来自风格生成或用户上传）
    - 否则使用内置模板
    """
    if custom_html:
        template = Template(custom_html)
        html_content = template.render(**data)
    else:
        # 尝试加载内置模板，没有就用简单兜底
        try:
            env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
            template = env.get_template(f"{template_name}.html")
            html_content = template.render(**data)
        except Exception:
            # 最简单的兜底模板
            fallback = """
            <!DOCTYPE html><html><head><meta charset="utf-8">
            <style>body{font-family:sans-serif;padding:40px} h1{color:#1e40af}</style>
            </head><body>
            <h1>{{ name }}</h1>
            <p>{{ contact }}</p>
            <h2>个人总结</h2><p>{{ summary }}</p>
            </body></html>
            """
            html_content = Template(fallback).render(**data)

    output_dir = Path(settings.GENERATED_DIR) / str(user_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"resume_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.pdf"
    pdf_path = output_dir / filename

    print(f"pdf_path: {pdf_path}")
    print(f"html_content: {html_content}")
    HTML(string=html_content).write_pdf(str(pdf_path))
    return str(pdf_path)