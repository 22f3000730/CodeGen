# Use Python base image
FROM python:3.12-slim-trixie

# Create non-root user
RUN useradd -m -u 1000 user

# Copy UV directly from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Set UV cache in /tmp and HOME for the user
ENV UV_CACHE_DIR=/tmp/.cache/uv \
    HOME=/home/user

# Create cache directory with proper permissions
RUN mkdir -p /tmp/.cache/uv && \
    chown -R user:user /tmp/.cache && \
    chmod -R 777 /tmp/.cache

# Copy files first (as root)
COPY pyproject.toml ./
COPY main.py llm_utils.py ./

# Set proper permissions
RUN chown -R user:user /app && \
    chmod -R 755 /app

# Switch to user and install dependencies
USER user
RUN /bin/uv sync

# Run the application
CMD ["/bin/uv", "run", "main.py"]