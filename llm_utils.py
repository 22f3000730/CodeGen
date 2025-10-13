# llm_utils.py
import os
import openai
from openai import OpenAI
import re
import json
from typing import Optional, List, Dict, Any

def generate_app_files(brief: str, checks: str, attachments: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    api_key = os.getenv("AI_API_KEY")
    if not api_key:
        raise RuntimeError("AI_API_KEY environment variable is required")

    client = OpenAI(api_key=api_key,base_url="https://aipipe.org/openai/v1")
    # System message: instruct model to return only a JSON object with "index","README" and optional "assets"
    system_msg = (
        'You are to return a single-page project by implementing the user brief. It can be made with HTML, CSS and JS.'
        'The page should not mimic or pretend to be working but instead should provide a working implementation of the brief if not properly simulate it. Make sure it passes all the checks'
        'Respond with a single valid JSON object and nothing else. The JSON must '
        'contain at least two keys: "index" (the complete index.html content for a '
        'single-page app that implements the brief) and "README" (the README.md text). '
        'Optionally include "assets" whose value is an object mapping filenames (e.g. "sample.png", "script.js") '
        'to file contents. For binary assets you may embed data URIs (e.g. "data:image/png;base64,..."). '
        'Do not include any surrounding markdown or explanatory text—only valid JSON.'
    )

    # Prepare user message: include the brief and any attachments as JSON
    user_payload = {"brief": brief,"checks": checks}
    if attachments:
        # Attachments are expected to be list of {"name": ..., "url": ...} where url may be a data URI
        user_payload["attachments"] = attachments

    user_msg = json.dumps(user_payload, ensure_ascii=False, indent=2)

    resp = client.chat.completions.create(model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ])

    # Try to extract assistant content; support common response shapes
    content = None
    try:
        content = resp.choices[0].message.content
    except Exception:
        try:
            content = resp.choices[0].text
        except Exception:
            content = str(resp)

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
