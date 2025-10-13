# CodeGen

A FastAPI service that generates single-page web applications using AI. Part of TDS project 1.

## Features

- Generates web apps from text descriptions using LLM
- Creates GitHub repositories automatically
- Enables GitHub Pages hosting
- Handles evaluation submissions

## Setup

1. Create a `.env` file with:
   ```
   SECRET_KEY=your_secret
   GITHUB_TOKEN=your_github_token
   AI_API_KEY=your_ai_key
   ```

2. Install dependencies:
   ```
   uv sync
   ```

## Usage

Run the server:
```
uv run main.py
```

The server will listen on port 8000 for incoming task requests.
