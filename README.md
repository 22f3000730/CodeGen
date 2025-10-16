# CodeGen

A FastAPI service that generates single-page web applications using AI. This service takes natural language descriptions and automatically generates web applications, creates GitHub repositories, and handles deployments.

## Features

-  AI-powered web application generation
-  Automatic GitHub repository creation and management
-  GitHub Pages hosting setup
-  Built-in evaluation submission handling
-  Support for multi-round updates
-  Secure API with secret key authentication

## Requirements

- Python 3.10 or higher
- GitHub account with API access
- AI API key (OpenRouter)

## Setup

1. Clone the repository:
   ```bash
   git clone <repo url or ssh>
   cd codegen
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Create a `.env` file with your credentials:
   ```
   SECRET_KEY=your_secret
   GITHUB_TOKEN=your_github_token
   AI_API_KEY=your_ai_key
   ```

4. Install dependencies:
   ```bash
   uv sync
   ```

5. Install development dependencies:
   ```bash
   uv sync -G dev
   ```

## Usage

Start the development server:
```bash
uvicorn main:app --reload
```

The server will listen on `http://localhost:8000` for incoming task requests.

### API Endpoints

- `GET /`: Health check endpoint
- `POST /task1`: Main endpoint for task processing
  - Requires authentication via `secret` field
  - Handles both initial creation (round 1) and updates (round > 1)
  - Returns repository and GitHub Pages URLs

## License

MIT License - See LICENSE file for details
