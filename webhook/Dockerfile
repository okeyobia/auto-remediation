FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir flask>=3.0.0 docker>=7.0.0 kubernetes>=25.0.0 requests>=2.31.0

# Copy app and modules
COPY app.py .
COPY slack.py .
COPY k8s.py .

CMD ["python", "app.py"]