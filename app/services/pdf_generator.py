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
    自动根据岗位要求的语言（中文/英文）生成对应语言的简历
    """
    llm = get_llm()

    # 简单判断岗位要求主要是中文还是英文
    def is_chinese(text: str) -> bool:
        if not text:
            return True
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        return chinese_chars / max(len(text), 1) > 0.15  # 超过15%中文字符就认为是中文

    target_lang = "中文" if is_chinese(job_description) or is_chinese(job_title) else "英文"

    if style_description:
        style_prompt = f"\n风格要求：{style_description}（请严格遵循这个视觉风格来设计排版和配色）"
    else:
        style_prompt = "\n风格要求：现代、专业、简洁，使用蓝色系作为点缀色，适合互联网和技术岗位。"

    # 语言强约束
    if target_lang == "中文":
        lang_instruction = """
【语言要求 - 非常重要】
- 岗位要求是中文，因此整份简历必须使用【中文】撰写。
- 姓名、公司名、学校名等专有名词保持原样，其余所有内容（总结、经历描述、技能等）全部用中文。
- 禁止出现英文句子（专有名词除外）。
"""
    else:
        lang_instruction = """
【Language Requirement - Very Important】
- The job requirements are in English, so the entire resume MUST be written in【English】.
- All content including summary, work experience, project descriptions, skills etc. must be in professional English.
- Do not use Chinese characters except for proper nouns if they originally appear in Chinese.
"""

    prompt = f"""你是专业的简历设计师和优化专家。请根据用户资料和目标岗位，直接生成一份完整、精美的 HTML 简历。

目标岗位：{job_title}
公司：{company or "未指定"}
岗位要求：
{job_description}

用户已有资料：
{json.dumps(user_data, ensure_ascii=False, indent=2)}
{style_prompt}
{lang_instruction}

硬性要求：
1. 必须返回完整的 HTML 文档，包含 <!DOCTYPE html>、<html>、<head>、<style>、<body>
2. 必须使用 @page {{ size: A4; margin: 1.5cm 1.8cm; }} 设置纸张和边距
3. 必须包含以下部分（用户资料中有的信息一定要写进去，不要只写总结）：
   - 姓名 + 联系方式（顶部）
   - 个人总结（针对岗位优化）
   - 工作经历（公司、职位、时间、要点列表）
   - 项目经历
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