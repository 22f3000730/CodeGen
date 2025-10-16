# llm_utils.py
import os
import requests
import re
import json
from typing import Optional, List, Dict, Any
from github import Github

def generate_app_files(brief: str, checks: List[str], attachments: Optional[List[Dict[str, str]]] = None, round: int = 1, task: str = None) -> Dict[str, Any]:
    api_key = os.getenv("AI_API_KEY")
    github_token = os.getenv("GITHUB_TOKEN")
    if not api_key:
        raise RuntimeError("AI_API_KEY environment variable is required")

    # Get existing code for rounds > 1
    existing_files = {}
    if round > 1 and github_token and task:
        try:
            g = Github(github_token)
            user = g.get_user()
            # Just use the task name as repo name, don't include user login
            repo = g.get_repo(f"{user.login}/{task}")
            for filename in ["index.html", "README.md"]:
                try:
                    file_content = repo.get_contents(filename)
                    existing_files[filename] = file_content.decoded_content.decode('utf-8')
                except Exception as e:
                    print(f"Failed to fetch {filename}: {str(e)}")
        except Exception as e:
            print(f"Failed to access repository: {str(e)}")

    # Modify system message to include context for updates
    system_msg = (
        'Create a single-page web application that implements the requirements.\n\n'
        'Output format - JSON object with:\n'
        '- "index": Complete HTML file with implementation\n'
        '- "README": Documentation markdown file following this structure:\n'
        '   1. Summary/Overview of the application\n'
        '   2. Setup instructions\n'
        '   3. Usage guide with examples\n'
        '   4. Code explanation and architecture\n'
        '   5. License information (MIT License)\n\n'
        'Technical requirements:\n'
        '1. Process data client-side\n'
        '2. CDN requirements:\n'
        '   - Use cdnjs.cloudflare.com as primary CDN provider\n'
        '   - Use latest stable versions with specific version numbers\n'
        '   - Preferred format: https://cdnjs.cloudflare.com/ajax/libs/LIBRARY/VERSION/FILE.min.js\n'
        '3. Base64 handling:\n'
        '   - Keep ${...} strings in data URIs as-is\n'
        '   - Do not try to decode template literals\n'
        '   - Example: data:text/csv;base64,${someBase64} should be used directly\n'
        '4. Match exact IDs from brief\n'
        '5. Handle all test conditions\n\n'
        'Best practices:\n'
        '- Process encoded data at runtime\n'
        '- Keep template literals intact\n'
        '- Include error handling\n'
        '- Verify all test checks pass'
    )

    if round > 1 and existing_files:
        system_msg += (
            '\n\nUpdate mode:\n'
            '- Use existing files as base\n'
            '- Preserve working features\n'
            '- Add new requirements\n'
            '- Maintain code structure\n'
            '- Use the attachments if provided\n'
        )

    # Prepare messages and make direct request to OpenRouter
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Prepare user message with clearer context
    user_payload = {
        "brief": brief,
        "checks": checks,
        "attachments": attachments,
        "round": round,
        "note": "Important: Keep ${...} template literals intact in data URIs"
    }
    if existing_files:
        user_payload["existing_files"] = existing_files

    payload = {
        "model": "qwen/qwen3-coder",
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, indent=2)}
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

    # Fallback: return the assistant output as the index.html and a structured README
    readme_template = f"""# {brief}

## Summary
A web application that {brief.lower()}

## Setup
1. Clone the repository
2. Open index.html in a web browser
3. No additional setup required as all dependencies are loaded via CDN

## Usage
{content}

## Code Explanation
The application is built using vanilla JavaScript and processes data client-side.
Please refer to the code comments in index.html for detailed implementation details.

## License
MIT License

Copyright (c) {os.getenv('GITHUB_USER', '2024')}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""

    return {
        "index": content,
        "README": readme_template,
    }