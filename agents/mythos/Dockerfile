FROM python:3.12-slim
WORKDIR /app
COPY . /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CODING_PROVIDER=local \
    CODING_MODEL=qwen2.5-coder:7b \
    CODING_API_BASE=http://127.0.0.1:11434/v1 \
    CODING_AUTONOMY=3 \
    CODING_HOST=0.0.0.0 \
    CODING_PORT=8790 \
    CODING_ROOT=/workspace
RUN mkdir -p /workspace && chmod +x /app/agent.py
EXPOSE 8790
CMD ["python3", "agent.py", "serve"]
