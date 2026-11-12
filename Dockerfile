FROM python:3.12-slim
WORKDIR /app
COPY server /app/server
COPY web /app/web
RUN pip install --no-cache-dir -r /app/server/requirements.txt
WORKDIR /app/server
EXPOSE 8875
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8875"]
