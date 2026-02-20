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
│  │   - Stores time-series data                        │ │
│  └─────────────────────────────────────────────────────┘ │
│                               ▲                           │
│                               │ Metrics Query             │
│  ┌─────────────────────────────────────────────────────┐ │
│  │        Grafana (Port 3000)                          │ │
│  │   - Queries Prometheus for metrics                 │ │
│  │   - Evaluates alert rules                          │ │
│  │   - Sends firing alerts to webhook                 │ │
│  └─────────────────────────────────────────────────────┘ │
│                               ▲                           │
│                               │ HTTP POST                 │
│  ┌─────────────────────────────────────────────────────┐ │
│  │   Remediation Webhook (Port 5000)                   │ │
│  │   - Receives alert notifications from Grafana      │ │
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
├── prometheus.yml                # Prometheus scrape configuration
├── alert_rules.yml               # Deprecated: kept for reference (Prometheus alerts)
├── alertmanager.yml              # Deprecated: AlertManager config (no longer used)
├── skaffold.yaml                 # Skaffold config for K8s development
├── grafana/
│   └── provisioning/
│       ├── datasources/
│       │   └── prometheus.yml    # Grafana datasource configuration
│       ├── dashboards/
│       │   ├── dashboards.yml    # Dashboard provisioning config
│       │   └── nginx-monitoring.json  # Nginx monitoring dashboard
│       └── alerting/
│           ├── alerts.yml        # Grafana alert rules provisioning config
│           ├── alert-rules.json  # Nginx alert rule definition
│           ├── contact-points.yml # Webhook notification receiver
│           └── notification-policy.yml # Alert routing policy
├── kube/                         # Kubernetes manifests & docs
│   ├── README.md                 # Kubernetes deployment guide
│   ├── 01-namespace.yaml
│   ├── 02-configmaps.yaml
│   ├── 03-secrets.yaml
│   ├── 04-pvcs.yaml
│   ├── 05-rbac.yaml
│   ├── 06-nginx.yaml
│   ├── 07-nginx-exporter.yaml
│   ├── 08-prometheus.yaml
│   ├── 09-alertmanager.yaml
│   ├── 10-grafana.yaml
│   ├── 11-webhook.yaml
│   └── 12-ingress.yaml
├── helm/                         # Helm chart for K8s deployment
│   └── aiops/
│       ├── Chart.yaml
│       ├── values.yaml
│       └── README.md
├── nginx/
│   ├── Dockerfile                # Custom Nginx with stub_status enabled
│   └── nginx.conf                # Nginx configuration
└── webhook/
    ├── app.py                    # Flask webhook receiver and remediation logic
    ├── slack.py                  # Slack notification handler
    ├── k8s.py                    # Kubernetes API client for pod restarts
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

2. **(Optional) Configure Slack integration:**
   ```bash
   export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
   ```
   See [Slack Setup](#slack-setup) section below for instructions.

3. **Start all services:**
   ```bash
   docker-compose up -d
   ```

4. **Verify services are running:**
   ```bash
   docker-compose ps
   ```

### Accessing Services

| Service | URL | Purpose |
|---------|-----|---------|
| Nginx App | http://localhost:8080 | Application being monitored |
| Nginx Exporter | http://localhost:9113/metrics | Prometheus metrics endpoint |
| Prometheus | http://localhost:9090 | Metrics storage & queries |
| Grafana | http://localhost:3000 | Monitoring, dashboards, & alerting |
| Webhook | http://localhost:5000/alert | Alert receiver endpoint |

**Note:** AlertManager (port 9093) is deprecated and no longer used in this architecture.

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

### Grafana Alerting (`grafana/provisioning/alerting/`)

Grafana unified alerting configured with:
- **Alert Rules** (`alert-rules.json`): Defines alert conditions (e.g., nginx_up == 0 for 30s)
- **Contact Points** (`contact-points.yml`): Webhook receiver pointing to `http://remediation_webhook:5000/alert`
- **Notification Policy** (`notification-policy.yml`): Routes alerts to the webhook receiver

**Alert Rule:** Fires when `nginx_up == 0` for 30+ seconds, then sends notification to webhook

**Login to Grafana:** http://localhost:3000 (admin/admin) to manage alerts

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

### Grafana (`grafana/provisioning/`)

Auto-configured Grafana instance with:
- **Datasource**: Prometheus is automatically added as the default datasource
- **Dashboard**: Pre-built "Nginx Monitoring" dashboard showing:
  - Nginx status (UP/DOWN)
  - Total HTTP requests
  - Active connections (reading, writing, waiting)
  - Request rate (5-minute average)

**Login Credentials:**
- Username: `admin`
- Password: `admin`

**Access the dashboard at:** http://localhost:3000

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

## 📦 Dependencies

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

## 📊 How It Works

1. **Metrics Collection**: Nginx Exporter exposes nginx metrics
2. **Scraping**: Prometheus scrapes metrics every 15 seconds from Nginx Exporter
3. **Storage**: Prometheus stores time-series data
4. **Querying**: Grafana queries Prometheus for real-time metrics
5. **Alert Evaluation**: Grafana evaluates alert rules (e.g., nginx_up == 0 for 30s)
6. **Alert Firing**: When condition is met, Grafana fires an alert
7. **Notification**: Grafana sends alert via webhook to remediation endpoint
8. **Remediation**: Webhook service automatically restarts the Nginx container
9. **Visualization**: Grafana dashboard displays metrics and alert status
10. **Resolution**: When Nginx recovers (nginx_up == 1), alert resolves

## 🧪 Testing

### View Grafana Dashboard

1. **Access Grafana:**
   - Open http://localhost:3000
   - Login with `admin` / `admin`
   - Navigate to **Dashboards** > **Nginx Monitoring**

2. **Dashboard displays:**
   - Nginx operational status (UP/DOWN gauge)
   - Total HTTP requests over time
   - Active connections (reading, writing, waiting)
   - Request rate (5-minute moving average)

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

### Health Check Endpoint

**GET** `/health`

Check webhook service health and configuration status.

**Response:**
```json
{
  "status": "healthy",
  "slack_enabled": true
}
```

Use this endpoint to verify the webhook is running and confirm if Slack integration is enabled.

## ☸️ Kubernetes Deployment

Deploy AIOps to Kubernetes for production environments with high availability, auto-scaling, and cloud-native architecture.

### Quick Start with kubectl

```bash
# 1. Build webhook container
docker build -t aiops-webhook:latest ./webhook

# 2. Apply all Kubernetes manifests
kubectl apply -f kube/

# 3. Verify deployment
kubectl get pods -n aiops
```

### Configuration

**Set Slack webhook (optional):**
```bash
kubectl create secret generic slack-credentials \
  --from-literal=webhook-url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL" \
  -n aiops --dry-run=client -o yaml | kubectl apply -f -
```

**Access services via port forwarding:**
```bash
kubectl port-forward -n aiops svc/grafana 3000:3000
kubectl port-forward -n aiops svc/prometheus 9090:9090
```

### Using Helm (Recommended)

Deploy using Helm for easier management:

```bash
# 1. Build webhook container
docker build -t aiops-webhook:latest ./webhook

# 2. Install Helm chart
helm install aiops helm/aiops -n aiops --create-namespace \
  --set webhook.image=aiops-webhook:latest

# 3. Verify installation
helm status aiops -n aiops
```

**Upgrade configurations:**
```bash
helm upgrade aiops helm/aiops -n aiops \
  --set slack.enabled=true \
  --set slack.webhookUrl="https://hooks.slack.com/services/..."
```

See [kube/README.md](kube/README.md) and [helm/aiops/README.md](helm/aiops/README.md) for comprehensive Kubernetes deployment documentation.

### Key Features

- **High Availability:** Multi-replica deployments with PodDisruptionBudgets
- **Persistent Storage:** Grafana and Prometheus data persistence
- **Auto-Remediation:** Webhook triggers Kubernetes API for pod restarts
- **Service Mesh Ready:** No sidecar injection required
- **RBAC Enabled:** Minimal permissions via ServiceAccount and Role
- **Ingress Support:** Built-in ingress configuration for external access

### Architecture

Kubernetes deployment uses:
- **Deployments** for stateless services (Nginx, exporters, AlertManager, webhook)
- **StatefulSets** (optional) for stateful services if needed
- **Services** for internal communication
- **PersistentVolumeClaims** for Prometheus and Grafana data
- **ConfigMaps** for configuration
- **Secrets** for sensitive data (Slack webhook)
- **RBAC** for webhook Kubernetes API access

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

## � Slack Setup

### Enable Slack Notifications

The webhook supports sending alert notifications to Slack. To enable it:

1. **Create a Slack Webhook URL:**
   - Go to https://api.slack.com/apps
   - Create a new app or select an existing one
   - Enable Incoming Webhooks
   - Create a new webhook for your desired channel
   - Copy the webhook URL

2. **Set the webhook URL:**
   ```bash
   export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
   ```

3. **Restart the webhook service:**
   ```bash
   docker-compose restart webhook
   ```

4. **Verify Slack is enabled:**
   ```bash
   curl http://localhost:5000/health | jq '.slack_enabled'
   ```

### Slack Messages

The system sends three types of Slack messages:

1. **Alert Firing:** 🚨 When an alert condition is triggered
   - Shows alert name and timestamp
   - Includes color coding (red for firing, green for resolved)

2. **Remediation Success:** ✓ When a container is successfully restarted
   - Shows the action taken
   - Includes container name and alert details
   - Blue color indicates success

3. **Remediation Failure:** ✗ When container restart fails
   - Shows the error message
   - Help with troubleshooting
   - Orange color indicates failure

### Example Slack Alert

When Nginx goes down, you'll receive messages like:
- **Alert:** 🚨 FIRING: NginxDown
- **Action:** 🔧 Remediation: ✓ Success - Container restarted

#### Firing Alert Webhook Payload

```json
{
  "text": "🚨 FIRING: nginx_down",
  "attachments": [{
    "color": "#FF0000",
    "fields": [
      {"title": "Alert", "value": "nginx_down", "short": true},
      {"title": "Status", "value": "firing", "short": true},
      {"title": "Container", "value": "nginx_app", "short": false},
      {"title": "Timestamp", "value": "2024-01-15 14:23:45 UTC", "short": false}
    ]
  }]
}
```

#### Remediation Success Webhook Payload

```json
{
  "text": "✓ Remediation: Success",
  "attachments": [{
    "color": "#0099FF",
    "fields": [
      {"title": "Action", "value": "nginx_down remediation executed successfully", "short": false},
      {"title": "Container", "value": "nginx_app", "short": true},
      {"title": "Alert", "value": "nginx_down", "short": true},
      {"title": "Timestamp", "value": "2024-01-15 14:24:05 UTC", "short": false}
    ]
  }]
}
```

#### Resolved Alert Webhook Payload

```json
{
  "text": "✅ RESOLVED: nginx_down",
  "attachments": [{
    "color": "#00FF00",
    "fields": [
      {"title": "Alert", "value": "nginx_down", "short": true},
      {"title": "Status", "value": "resolved", "short": true},
      {"title": "Container", "value": "nginx_app", "short": false},
      {"title": "Timestamp", "value": "2024-01-15 14:25:30 UTC", "short": false}
    ]
  }]
}
```

## �📝 Extending the System

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
