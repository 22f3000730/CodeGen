# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests,time, os
from dotenv import load_dotenv
from github import Github  # from PyGithub
from llm_utils import generate_app_files  # your LLM logic
from typing import Optional, List, Dict

app = FastAPI()
load_dotenv()  # take environment variables from .env

SHARED_SECRET = os.getenv("SECRET_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

class TaskRequest(BaseModel):
    email: str
    task: str
    brief: str
    checks: List[str]
    round: int
    nonce: str
    secret: str
    evaluation_url: str
    attachments: Optional[List[Dict[str, str]]] = None  # added to accept attachments like data URIs

@app.get("/")
def root():
    return {"status": "ok"}
@app.post("/task1")
async def handle_task(req: TaskRequest):
    # 1. Secret verification
    if req.secret != SHARED_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")

    # 2. Generate files and handle repo based on round
    app_files = generate_app_files(
        brief=req.brief, 
        checks=req.checks, 
        attachments=req.attachments,
        round=req.round,
        task=req.task
    )

    # Validate LLM output
    if not isinstance(app_files, dict) or "index" not in app_files or "README" not in app_files:
        raise HTTPException(status_code=500, detail="LLM did not return expected file structure")

    # Initialize GitHub client
    g = Github(GITHUB_TOKEN)
    user = g.get_user()
    repo_name = f"{req.task}"

    if req.round == 1:
        # Round 1: Create new repo
        try:
            repo = user.create_repo(repo_name, private=False, auto_init=False, license_template="mit")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create repo: {e}")
    else:
        # Round >1: Get existing repo and update
        try:
            # Use get_repo with full path
            repo = g.get_repo(f"{user.login}/{repo_name}")
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Repository not found: {e}")

    # Prepare files to commit
    files_to_commit = {
        "index.html": app_files["index"],
        "README.md": app_files["README"],
    }
    if isinstance(app_files.get("assets"), dict):
        files_to_commit.update(app_files["assets"])

    # Add/Update files & commit
    for path, content in files_to_commit.items():
        try:
            if req.round == 1:
                # Create new file for round 1
                repo.create_file(path, f"add {path}", content)
            else:
                # Update existing file for later rounds
                try:
                    # Get current file content
                    file = repo.get_contents(path)
                    # Update file
                    repo.update_file(path, f"update {path} for round {req.round}", content, file.sha)
                except Exception:
                    # File doesn't exist, create it
                    repo.create_file(path, f"add {path} for round {req.round}", content)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to handle file {path}: {e}")

    # Enable GitHub Pages only for round 1
    if req.round == 1:
        try:
            requests.post(
                f"https://api.github.com/repos/{user.login}/{repo_name}/pages",
                headers={
                    "Authorization": f"token {GITHUB_TOKEN}",
                    "Accept": "application/vnd.github.v3+json",
                },
                json={"source": {"branch": "main", "path": "/"}}
            )
        except Exception:
            pass

    # Get latest commit SHA
    commit_sha = repo.get_commits()[0].sha

    # Prepare evaluation JSON
    payload = {
        "email": req.email,
        "task": req.task,
        "round": req.round,
        "nonce": req.nonce,
        "repo_url": repo.html_url,
        "commit_sha": commit_sha,
        "pages_url": f"https://{user.login}.github.io/{repo_name}/",
    }


    time.sleep(60)

    # 8. POST to evaluation URL (with exponential backoff) — include JSON Content-Type & try up to 5 times
    delay = 1
    headers = {"Content-Type": "application/json"}
    for _ in range(5):
        try:
            r = requests.post(req.evaluation_url, json=payload, headers=headers, timeout=10)
            if r.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(delay)
        delay *= 2

    return {
        "repository_url": repo.html_url,
        "commit_sha": commit_sha,
        "pages_url": f"https://{user.login}.github.io/{repo_name}/"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)