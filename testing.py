from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import os
import argparse
import uvicorn
import json

app = FastAPI()

# Define expected payload structure
class EvaluationPayload(BaseModel):
    email: str
    task: str
    round: int
    nonce: str
    repo_url: str
    commit_sha: str
    pages_url: str

@app.post("/")
async def incoming(request: Request):
    print("\n=== Incoming Evaluation Request ===")
    
    # Log request metadata
    try:
        print(f"Method: {request.method}")
        print("\nHeaders:")
        for k, v in request.headers.items():
            print(f"  {k}: {v}")
    except Exception as e:
        print(f"Error reading request metadata: {e}")

    # Parse and validate payload
    try:
        data = await request.json()
        print("\nRaw payload:")
        print(json.dumps(data, indent=2))
        
        # Validate against expected structure
        payload = EvaluationPayload(**data)
        
        print("\nValidated fields:")
        print(f"Email: {payload.email}")
        print(f"Task: {payload.task}")
        print(f"Round: {payload.round}")
        print(f"Nonce: {payload.nonce}")
        print(f"Repo URL: {payload.repo_url}")
        print(f"Commit SHA: {payload.commit_sha}")
        print(f"Pages URL: {payload.pages_url}")
        
        return {"status": "ok", "message": "Evaluation payload received and validated"}
    
    except Exception as e:
        error = f"Invalid payload structure: {str(e)}"
        print(f"\nError: {error}")
        raise HTTPException(status_code=400, detail=error)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run dummy FastAPI server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "5000")), help="Port to listen on")
    args = parser.parse_args()
    print(f"Starting evaluation test server on {args.host}:{args.port}")
    print("Waiting for POST requests matching the evaluation payload structure...")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")