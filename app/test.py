#
# from langchain_openai import ChatOpenAI
# from langchain_ollama import ChatOllama
#
# # llm = ChatOpenAI(
# #     base_url="http://192.168.1.24:8000/v1",  # 必须加上 /v1 后缀
# #     model="/app/models/Qwen3.8-27B-ROCmFP4-FAST.gguf",  # 传入 /models 中返回的准确名称或 id
# #     api_key="no-key-required",  # llama-server 不需要真实 key，但 LangChain 校验需要填任意非空字符串
# #     temperature=0.1,
# #     timeout=120.0
# # )
#
# llm = ChatOllama(
#     model="qwen3.8:latest",
#     base_url="http://192.168.1.24:11434",
#     temperature=0.1
# )
#
# # 测试调用
#
# with open("prompt.txt", "r", encoding="utf-8") as f:
#     content = f.read()
#
# # response = llm.invoke(content)
# # print(response.content)
#
# # 使用 stream 方法替代 invoke
# for chunk in llm.stream(content):
#     print(chunk.content, end="", flush=True)
#


from weasyprint import HTML
print("WeasyPrint 加载成功！")

html_content = """
<!DOCTYPE html><html><head><meta charset="utf-8">
            <style>body{font-family:sans-serif;padding:40px} h1{color:#1e40af}</style>
            </head><body>
            <h1>Zhao Ze (Coki Zhao)</h1>
            <p>+86 180 5175 8839 | xiao230coki@gmail.com | Suzhou, China</p>
            <h2>个人总结</h2><p>Senior Java Backend Engineer with 16+ years of enterprise-grade development experience, including direct work on LSEG (London Stock Exchange Group) high-concurrency communication systems and financial-sector projects (China Construction Bank). Deep expertise in Java microservices architecture (Spring Boot / Spring Cloud), JVM internals, multithreading & concurrency control, and distributed middleware (Redis, Kafka, RocketMQ). Proven track record in designing high-performance, high-availability, and highly scalable core systems with MySQL index optimization and performance tuning. Adept at cross-functional collaboration with product managers and front-end teams to deliver mission-critical financial and exchange platforms under tight deadlines.</p>
            </body></html>
"""
pdf_path = "generated/2/resume_20260923_111347_d1d878.pdf"

HTML(string=html_content).write_pdf(str(pdf_path))
