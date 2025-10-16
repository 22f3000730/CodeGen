# llm_utils.py
import os
import requests
import re
import json
from typing import Optional, List, Dict, Any

def generate_app_files(brief: str, checks: List[str], attachments: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    api_key = os.getenv("AI_API_KEY")
    if not api_key:
        raise RuntimeError("AI_API_KEY environment variable is required")

    # System message: instruct model to return only a JSON object with "index","README" and optional "assets"
    system_msg = (
        'Build a web page according to brief requirements. Return ONLY a JSON object with:\n'
        '"index": Complete HTML with working implementation\n'
        '"README": Brief documentation\n\n'
        'Rules:\n'
        '- Use Appropriate Javascript libraries if required, CDN can be used\n'
        '- Follow brief EXACTLY\n'
        '- Match ID names precisely\n'
        '- Make every check pass\n'
        '- Process data client-side\n'
        '- No placeholder/mock functionality'
    )

    # Prepare messages and make direct request to OpenRouter
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "qwen/qwen3-coder",
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": json.dumps({"brief": brief, "checks": checks, "attachments": attachments}, ensure_ascii=False, indent=2)}
        ]
    }

    resp = requests.post(
        "https://aipipe.org/openrouter/v1/chat/completions",
        headers=headers,
        json=payload
    )

    if not resp.ok:
        raise RuntimeError(f"API request failed: {resp.status_code} {resp.text}")

    # Extract content from OpenRouter response format
    try:
        content = resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        content = str(resp.text)

    # Attempt to extract JSON substring if wrapped in markdown or extra text
    json_obj = None
    try:
        json_obj = json.loads(content)
    except Exception:
        # Try to find the first {...} JSON block (non-greedy to avoid trailing text)
        m = re.search(r"\{(?:[^{}]|(?R))*\}", content, re.S) if hasattr(re, 'R') else re.search(r"\{.*\}", content, re.S)
        if m:
            try:
                json_obj = json.loads(m.group(0))
            except Exception:
                json_obj = None

    # If parsing succeeded and has required keys, normalize and return it
    if isinstance(json_obj, dict) and "index" in json_obj and "README" in json_obj:
        result = {"index": json_obj["index"], "README": json_obj["README"]}
        assets = json_obj.get("assets")
        if isinstance(assets, dict):
            # Ensure asset keys and values are strings
            sanitized_assets: Dict[str, str] = {}
            for k, v in assets.items():
                if isinstance(k, str) and (isinstance(v, str) or v is None):
                    sanitized_assets[k] = v or ""
            if sanitized_assets:
                result["assets"] = sanitized_assets
        return result

    # Fallback: return the assistant output as the index.html and a basic README
    return {
        "index": content,
        "README": f"# {brief}\n\n{content}",
    }