FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app/backend
COPY backend/requirements.txt ./requirements.txt
# No GUI is used in the container; keep the same OpenCV version without desktop libraries.
RUN sed -i 's/^opencv-python==/opencv-python-headless==/' requirements.txt && pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY backend/migrations ./migrations
COPY backend/alembic.ini ./alembic.ini
RUN useradd --uid 10001 --create-home scoutai && mkdir -p /data/uploads && chown -R scoutai:scoutai /data
USER scoutai
CMD ["python", "-m", "uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
