# Use Python base image
FROM python:3.12-slim-trixie

# Copy UV directly from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy only dependency files first
COPY pyproject.toml ./

# Install dependencies using UV sync
RUN /bin/uv sync

# Now copy application files
COPY main.py llm_utils.py ./

# Run the application using UV
CMD ["/bin/uv", "run", "main.py"]