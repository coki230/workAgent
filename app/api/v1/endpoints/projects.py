from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.model.models import Project
from app.schema.schemas import ProjectOut, ProjectCreate
from app.services.github_service import fetch_github_repos
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