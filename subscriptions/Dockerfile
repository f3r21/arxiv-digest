FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./
COPY arxiv_categories.json ./
COPY templates ./templates
COPY static ./static
COPY tests ./tests

# Trust X-Forwarded-For so request.client.host (and the slowapi rate limit)
# sees the visitor, not Caddy. "*" is safe here because port 8000 is not
# published to the host in either compose file, so only containers on the
# internal network can reach uvicorn, and Caddy overwrites the header with
# the real peer address (header_up X-Forwarded-For {remote_host}).
# Override with a CIDR (e.g. FORWARDED_ALLOW_IPS=172.18.0.0/16) in .env if
# that ever changes.
ENV FORWARDED_ALLOW_IPS="*"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
