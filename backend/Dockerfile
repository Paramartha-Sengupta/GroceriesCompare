FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
ENV PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=""
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
