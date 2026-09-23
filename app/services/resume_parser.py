import json
import pdfplumber

from app.services.llm_service import get_llm


def extract_text_from_pdf(file_path: str) -> str:
    texts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                texts.append(text)
    return "\n".join(texts)

def structure_resume_with_llm(raw_text: str) -> dict:
    llm = get_llm()
    prompt = f"""请把下面这份简历文本严格转换成 JSON，只返回合法 JSON，不要任何解释。

字段要求：
{{
  "personal_info": {{"name": "", "email": "", "phone": "", "location": ""}},
  "education": [],
  "work_experience": [],
  "projects": [],
  "skills": [],
  "certificates": [],
  "others": ""
}}

简历原文：
{raw_text[:12000]}
"""
    import app.utils.file as file_utils
    file_utils.str_2_file("prompt.txt", prompt)

    response = llm.invoke(prompt)
    content = response.content.strip()
    # 简单清理可能的 markdown 代码块
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    return json.loads(content)