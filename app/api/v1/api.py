from fastapi import APIRouter

from app.api.v1.endpoints import resumes, projects, generate, auth

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["resumes"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(generate.router, prefix="/generate", tags=["generate"])