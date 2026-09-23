from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.model.models import Project, User
from app.schema.schemas import ProjectOut, ProjectCreate
from app.services.github_service import fetch_github_repos
from app.services.url_analyzer import analyze_url_to_project
from app.session import get_db
from app.utils.deps import get_current_user_id, get_or_create_user

router = APIRouter()

@router.post("/github", response_model=list[ProjectOut])
async def add_github_projects(
    body: ProjectCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_or_create_user(user_id, db)

    if not body.github_username:
        raise HTTPException(400, "请提供 github_username")

    repos = await fetch_github_repos(body.github_username)
    created = []

    for repo in repos:
        project = Project(
            user_id=user_id,
            name=repo["name"],
            github_url=repo["github_url"],
            description=repo["description"],
            languages=repo["languages"],
            stars=repo["stars"],
            extra_info={"source": "github", "note": body.extra_info} if body.extra_info else None
        )
        db.add(project)
        created.append(project)

    db.commit()
    for p in created:
        db.refresh(p)
    return created

@router.get("/", response_model=list[ProjectOut])
def list_projects(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    return db.query(Project).filter(Project.user_id == user_id).all()

class UrlProjectRequest(BaseModel):
    url: str

@router.post("/from-url", summary="从网址分析并添加项目经验")
async def add_project_from_url(
    body: UrlProjectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        project_data = await analyze_url_to_project(body.url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"分析网址失败：{str(e)}")

    # 写入数据库
    project = Project(
        user_id=current_user.id,
        name=project_data.get("name"),
        github_url=project_data.get("url") if project_data.get("source_type") == "github" else None,
        description=project_data.get("description"),
        languages=project_data.get("technologies") or [],
        readme_content="",
        stars=0,
        extra_info={
            "highlights": project_data.get("highlights", []),
            "period": project_data.get("period", ""),
            "source_type": project_data.get("source_type"),
            "original_url": body.url
        }
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    return {
        "message": "项目已成功分析并保存",
        "project": {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "highlights": project_data.get("highlights", []),
            "technologies": project_data.get("technologies", []),
            "url": body.url
        }
    }