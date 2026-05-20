FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./
COPY arxiv_categories.json ./
COPY templates ./templates
COPY static ./static
COPY tests ./tests

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
