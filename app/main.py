from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os

from app.api.v1.api import api_router
from app.config import get_settings
from app.model.base import Base
from app.session import engine

settings = get_settings()

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 确保目录存在
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.GENERATED_DIR, exist_ok=True)

app = FastAPI(title="Resume Agent", version="0.1.0")

# 注册 API 路由
app.include_router(api_router, prefix="/api/v1")

# 模板目录（项目根目录下的 templates）
BASE_DIR = Path(__file__).resolve().parent  # 根据实际路径调整
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# 可选：静态文件
# app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html"
    )

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="register.html"
    )

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html"
    )

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html"
    )

if __name__ == '__main__':
    # 注意：在代码中传参时，使用 app 变量本身或字符串 "app.main:app"
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)