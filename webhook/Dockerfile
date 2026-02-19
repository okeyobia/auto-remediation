FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir flask>=3.0.0 docker>=7.0.0

# Copy app
COPY app.py .

CMD ["python", "app.py"]