import httpx
from typing import List, Dict

async def fetch_github_repos(username: str) -> List[Dict]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"https://api.github.com/users/{username}/repos?per_page=100&sort=updated")
        resp.raise_for_status()
        repos = resp.json()

        results = []
        for repo in repos:
            if repo.get("fork"):
                continue
            results.append({
                "name": repo["name"],
                "github_url": repo["html_url"],
                "description": repo.get("description") or "",
                "languages": [repo.get("language")] if repo.get("language") else [],
                "stars": repo.get("stargazers_count", 0),
                "readme_content": ""  # 可后续再拉取 README
            })
        return results