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

    # 2. Generate minimal app files (with your LLM) — pass attachments through
    app_files = generate_app_files(req.brief, attachments=req.attachments)

    # Validate LLM output: expect dict with "index" and "README"
    if not isinstance(app_files, dict) or "index" not in app_files or "README" not in app_files:
        raise HTTPException(status_code=500, detail="LLM did not return expected file structure")

    # Map to actual repo file paths; include any optional assets returned by the LLM
    files_to_commit = {
        "index.html": app_files["index"],
        "README.md": app_files["README"],
    }
    # Accept optional assets dict: {"sample.png": "data:image/png;base64,...", "script.js": "..."}
    assets = app_files.get("assets") or {}
    for fname, content in assets.items():
        files_to_commit[fname] = content

    # 3. Create GitHub repo
    g = Github(GITHUB_TOKEN)
    user = g.get_user()
    repo_name = f"{req.task}"
    try:
        repo = user.create_repo(repo_name, private=False, auto_init=False, license_template="mit")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create repo: {e}")

    # 4. Add files & commit
    for path, content in files_to_commit.items():
        # If LLM provided a data URI for an asset, store it verbatim so index.html can reference it
        try:
            repo.create_file(path, f"add {path}", content)
        except Exception as e:
            # attempt to continue but surface error if all fails
            raise HTTPException(status_code=500, detail=f"Failed to create file {path}: {e}")

    # 5. Enable GitHub Pages (using API) — explicit source branch/path and Accept header
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
        # non-fatal; continue
        pass

    # 6. Fetch commit SHA
    commit_sha = repo.get_commits()[0].sha

    # 7. Prepare evaluation JSON
    payload = {
        "email": req.email,
        "task": req.task,
        "round": req.round,
        "nonce": req.nonce,
        "repo_url": repo.html_url,
        "commit_sha": commit_sha,
        "pages_url": f"https://{user.login}.github.io/{repo_name}/",
    }

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

    return {"status": "ok", "repo": repo.html_url, "commit": commit_sha}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)