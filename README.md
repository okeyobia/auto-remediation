# AIOps Auto-Remediation System

Automated remediation system that monitors Nginx using Prometheus and automatically restarts containers when alerts are triggered.

## 📋 Overview

This project implements an automated incident response platform that:
- **Monitors** Nginx container health using Prometheus and Nginx Prometheus Exporter
- **Detects** issues through predefined alert rules
- **Responds** automatically by restarting failed containers via webhook notifications
- **Manages** the entire stack using Docker Compose for easy deployment

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Docker Compose Stack                   │
├──────────────────────────────────────────────────────────┤
│                                                            │
│  ┌─────────────┐      ┌──────────────────────┐           │
│  │    Nginx    │      │  Nginx Prometheus    │           │
│  │  (Monitored)│◄─────┤     Exporter         │           │
│  └─────────────┘      └──────────────────────┘           │
│                               ▲                           │
│                               │ Metrics (Port 9113)       │
│  ┌─────────────────────────────────────────────────────┐ │
│  │           Prometheus (Port 9090)                    │ │
│  │   - Scrapes metrics from Nginx Exporter            │ │
│  │   - Evaluates alert rules                          │ │
│  └─────────────────────────────────────────────────────┘ │
│                               ▲                           │
│                               │ Alerts                    │
│  ┌─────────────────────────────────────────────────────┐ │
│  │        AlertManager (Port 9093)                     │ │
│  │   - Routes firing alerts to webhook receiver       │ │
│  └─────────────────────────────────────────────────────┘ │
│                               ▲                           │
│                               │ HTTP POST                 │
│  ┌─────────────────────────────────────────────────────┐ │
│  │   Remediation Webhook (Port 5000)                   │ │
│  │   - Receives alert notifications                   │ │
│  │   - Automatically restarts Nginx container         │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                            │
└──────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
.
├── README.md                     # This file
├── pyproject.toml                # Python project configuration (uv)
├── docker-compose.yml            # Docker Compose configuration
├── prometheus.yml                # Prometheus scrape and alert config
├── alertmanager.yml              # AlertManager routing config
├── alert_rules.yml               # Alert rules definitions
├── nginx/
│   ├── Dockerfile                # Custom Nginx with stub_status enabled
│   └── nginx.conf                # Nginx configuration
└── webhook/
    ├── app.py                    # Flask webhook receiver and remediation logic
    └── Dockerfile                # Webhook service container image
```

## 🚀 Quick Start

### Prerequisites
- Docker
- Docker Compose

### Installation & Deployment

1. **Clone and navigate to the project:**
   ```bash
   cd aiops-auto-rem
   ```

2. **Start all services:**
   ```bash
   docker-compose up -d
   ```

3. **Verify services are running:**
   ```bash
   docker-compose ps
   ```

### Accessing Services

| Service | URL | Purpose |
|---------|-----|---------|
| Nginx App | http://localhost:8080 | Application being monitored |
| Nginx Exporter | http://localhost:9113/metrics | Prometheus metrics endpoint |
| Prometheus | http://localhost:9090 | Monitoring UI & metrics queries |
| AlertManager | http://localhost:9093 | Alert management UI |
| Webhook | http://localhost:5000/alert | Alert receiver endpoint |

## 🔧 Running with `uv` (Local Development)

The project includes `uv` configuration for local development and testing of the webhook service independently. **Note:** `uv` is for local development only; Docker Compose uses standard pip for reliable container builds.

### Prerequisites
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) installed

### Local Webhook Development

1. **Install dependencies using uv:**
   ```bash
   uv sync
   ```

2. **Run the webhook locally:**
   ```bash
   uv run python webhook/app.py
   ```
   The webhook will be available at `http://localhost:5000`

3. **Run with watch mode (auto-restart on changes):**
   ```bash
   uv run --with watchfiles python -m watchfiles webhook.app:app --watch webhook
   ```

### Development Dependencies

Install optional development tools:
```bash
uv sync --extra dev
```

This includes:
- **pytest**: Unit testing
- **black**: Code formatting
- **ruff**: Linting

### Running Tests

```bash
uv run pytest
```

Run with coverage report:
```bash
uv run pytest --cov=webhook --cov-report=html
```

The test suite includes:
- **Endpoint tests**: Verify `/alert` endpoint functionality with firing/resolved alerts
- **Error handling**: Test error scenarios like container not found, invalid JSON
- **Multiple alerts**: Test handling of multiple alerts in a single request
- **Method validation**: Ensure only POST requests are allowed

### Code Formatting

```bash
# Format code
uv run black webhook/

# Check with ruff
uv run ruff check webhook/
```

## 📋 Deployment Options

### Option 1: Full Stack with Docker Compose (Recommended for Production)

Best for complete monitoring setup with Prometheus, AlertManager, Nginx, and webhook all containerized.

```bash
docker-compose up -d
```

**Advantages:**
- ✅ Complete isolated environment
- ✅ Reproducible across machines
- ✅ All services properly networked
- ✅ No local dependencies needed
- ✅ Easy to deploy to cloud/orchestration platforms

**Use case:** Production deployments, complete monitoring stack

### Option 2: Local Development with `uv` + Partial Docker Stack

Run webhook locally with `uv` while other services run in Docker.

```bash
# Start only the monitoring stack (Prometheus, AlertManager, Nginx)
docker-compose up -d prometheus alertmanager nginx nginx_exporter

# In another terminal, run webhook locally
uv run python webhook/app.py
```

**Advantages:**
- ✅ Fast feedback loop for webhook development
- ✅ Easy debugging with local Python stack
- ✅ Hot reload capability
- ✅ IDE integration and debugging tools

**Use case:** Webhook development, testing alert logic locally

### Option 3: Container with `uv` (Updated Dockerfile)

Dockerfile uses standard pip for reliable container builds.

```bash
docker-compose build webhook
docker-compose up -d
```

**Advantages:**
- ✅ Container isolation
- ✅ Reproducible builds
- ✅ No local dependencies needed

**Use case:** CI/CD pipelines, container registries

## 🔧 Configuration

### Nginx Configuration (`nginx/nginx.conf`)

Custom Nginx configuration with `stub_status` module enabled to expose metrics:
- Exposes `/stub_status` endpoint for Prometheus scraping
- Required for Nginx Prometheus Exporter to collect metrics
- Listens on port 80 with standard HTTP serving

### Alert Rules (`alert_rules.yml`)

Defines monitoring thresholds. Default rule:
- **NginxDown**: Triggers when Nginx is unreachable for 30 seconds

```yaml
NginxDown:
  condition: nginx_up == 0
  duration: 30s
  severity: critical
```

Note: Uses `nginx_up` metric exported by Nginx Prometheus Exporter, not the generic `up` metric.

### AlertManager (`alertmanager.yml`)

Routes firing alerts to the webhook service via Docker container hostname:
```yaml
webhook_configs:
  - url: 'http://remediation_webhook:5000/alert'
```

### Prometheus (`prometheus.yml`)

Configures metrics scraping and alert routing to AlertManager:
- **Scrape Interval**: 15 seconds
- **Scrape Target**: Nginx Exporter (port 9113)
- **Alerting**: Routes alerts to AlertManager (port 9093)

### Webhook Service (`webhook/app.py`)

Receives alerts and triggers automated remediation:
- Listens on port 5000
- Receives POST requests at `/alert` endpoint
- Restarts `nginx_app` container when firing alerts are received

## � Dependencies

### Python Dependencies

Managed in `pyproject.toml`:

- **flask** (>= 3.0.0): Web framework for webhook receiver
- **docker** (>= 7.0.0): Docker SDK for Python to control containers

### Optional Development Dependencies

- **pytest**: Unit testing framework
- **black**: Code formatter
- **ruff**: Fast Python linter

Install all dev dependencies with `uv`:
```bash
uv sync --extra dev
```

## �📊 How It Works

1. **Metrics Collection**: Nginx Exporter exposes nginx metrics
2. **Evaluation**: Prometheus scrapes metrics and evaluates alert rules every 15 seconds
3. **Alert Triggering**: Prometheus fires an alert if Nginx is down for 30 seconds
4. **Notification**: AlertManager routes the alert to the webhook endpoint
5. **Remediation**: Webhook service automatically restarts the Nginx container
6. **Resolution**: When Nginx recovers, a resolved notification is sent

## 🧪 Testing

### Manually trigger an alert:

1. **Stop the Nginx container:**
   ```bash
   docker-compose exec nginx nginx -s stop
   ```
   Or force kill it:
   ```bash
   docker-compose kill nginx
   ```

2. **Check AlertManager UI:**
   - Navigate to http://localhost:9093
   - You should see the `NginxDown` alert in firing state

3. **Observe auto-remediation:**
   - The webhook should receive the alert
   - Nginx container will automatically restart
   - Alert will transition to "resolved" status

### View logs:
```bash
# Webhook logs
docker-compose logs webhook -f

# Prometheus logs
docker-compose logs prometheus -f

# AlertManager logs
docker-compose logs alertmanager -f
```

## 🔌 API Endpoints

### Webhook Alert Endpoint

**POST** `/alert`

Receives alert notifications from AlertManager.

**Request body:**
```json
{
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "severity": "critical"
      },
      "annotations": {
        "description": "Nginx container is down"
      }
    }
  ]
}
```

**Response:**
```json
{
  "status": "processed"
}
```

## 🛠️ Troubleshooting

### Nginx not auto-restarting?

1. **Check webhook logs:**
   ```bash
   docker-compose logs webhook
   ```

2. **Verify Docker socket is mounted:**
   ```bash
   docker-compose ps webhook  # Check volumes
   ```

3. **Check AlertManager is routing alerts correctly:**
   ```bash
   docker-compose logs alertmanager
   ```

### Alerts not triggering?

1. **Verify Prometheus is scraping metrics:**
   - Go to http://localhost:9090/targets
   - Check if Nginx Exporter is "UP"

2. **Check alert rules are loaded:**
   - Go to http://localhost:9090/rules
   - Verify `nginx_alerts` group is present

### Container connectivity issues?

Ensure all services can reach each other:
```bash
docker-compose exec prometheus curl http://alertmanager:9093
docker-compose exec alertmanager curl http://webhook:5000/alert
```

## 📝 Extending the System

### Add new alert rules:
Edit `alert_rules.yml` and add new conditions to monitor:
```yaml
- alert: HighMemoryUsage
  expr: container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.8
  for: 5m
```

### Add new remediation actions:
Modify `webhook/app.py` to handle different alert names:
```python
if alert_name == "HighMemoryUsage":
    # Custom remediation logic
```

### Monitor additional services:
Add new services to `docker-compose.yml` with exporters, update Prometheus config, and define corresponding alert rules.

## 📜 License

[Add your license here]

## 👤 Author

[Add author information]

## 🤝 Contributing

[Add contribution guidelines]
