FROM python:3.12-slim
# Python 3.12 is required: pandas 2.2.3 ships pre-built cp312 wheels.
# pandas 2.2.0 had no cp312 wheel and required a C compiler to build from source.

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
