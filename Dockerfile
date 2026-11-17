FROM python:3.12-slim
WORKDIR /app
COPY server/requirements.txt /app/server/requirements.txt
RUN pip install --no-cache-dir -r /app/server/requirements.txt
COPY server /app/server
COPY web /app/web
WORKDIR /app/server
EXPOSE 8875
# Render injects PORT at runtime; Docker Compose keeps the local 8875 default.
CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8875}"]
