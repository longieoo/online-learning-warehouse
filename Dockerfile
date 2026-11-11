FROM python:3.12.8-slim-bookworm AS base
WORKDIR /app
COPY requirements.txt requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt
ENV PYTHONUNBUFFERED=1

FROM base AS runner
COPY . .
CMD ["python", "cli.py", "--help"]

FROM base AS dashboard
COPY demo/requirements.lock.txt /tmp/dashboard-requirements.lock.txt
RUN pip install --no-cache-dir -r /tmp/dashboard-requirements.lock.txt
COPY . .
ENV PYTHONPATH=/app
CMD ["streamlit", "run", "demo/app.py", "--server.address=0.0.0.0", "--server.headless=true"]
