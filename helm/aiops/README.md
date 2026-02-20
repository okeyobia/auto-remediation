# AIOps Helm Chart

Deploy AIOps auto-remediation system using Helm.

## Prerequisites

- Kubernetes 1.20+
- Helm 3.0+
- kubectl configured

## Installation

### 1. Build Webhook Image

```bash
docker build -t aiops-webhook:latest ../webhook/
```

If using a registry:
```bash
docker tag aiops-webhook:latest your-registry/aiops-webhook:latest
docker push your-registry/aiops-webhook:latest
```

### 2. Create Namespace

```bash
kubectl create namespace aiops
```

### 3. Install Chart

```bash
helm install aiops . -n aiops
```

Or with custom values:

```bash
helm install aiops . -n aiops \
  --set webhook.image=your-registry/aiops-webhook:latest \
  --set slack.enabled=true \
  --set slack.webhookUrl="https://hooks.slack.com/services/..."
```

### 4. Verify Installation

```bash
helm status aiops -n aiops
kubectl get pods -n aiops
```

## Configuration

### Enable Slack Integration

Edit `values.yaml`:

```yaml
slack:
  enabled: true
  webhookUrl: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

Or via Helm:

```bash
helm upgrade aiops . -n aiops \
  --set slack.enabled=true \
  --set slack.webhookUrl="https://hooks.slack.com/services/..."
```

### Scale Services

```bash
helm upgrade aiops . -n aiops \
  --set nginx.replicas=3 \
  --set webhook.replicas=3
```

### Change Storage Size

```bash
helm upgrade aiops . -n aiops \
  --set prometheus.storage.size=20Gi \
  --set grafana.storage.size=10Gi
```

### Customize Alert Rules

Edit `values.yaml` alertRules section or pass via `--set-json`:

```bash
helm upgrade aiops . -n aiops \
  --set-json 'alertRules=<json-file>'
```

## Uninstall

```bash
helm uninstall aiops -n aiops
kubectl delete namespace aiops
```

## Chart Values

Key configuration options in `values.yaml`:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `namespace` | Kubernetes namespace | `aiops` |
| `nginx.replicas` | Nginx replicas | `2` |
| `prometheus.storage.size` | Prometheus storage | `10Gi` |
| `grafana.storage.size` | Grafana storage | `5Gi` |
| `webhook.replicas` | Webhook replicas | `2` |
| `slack.enabled` | Enable Slack | `false` |
| `slack.webhookUrl` | Slack webhook URL | `` |
| `ingress.enabled` | Enable Ingress | `true` |

## Helm Lifecycle

### Upgrade Chart

```bash
helm upgrade aiops . -n aiops
```

### Rollback to Previous Version

```bash
helm rollback aiops -n aiops
```

### View Deployment History

```bash
helm history aiops -n aiops
```

## Troubleshooting

### Check Chart Syntax

```bash
helm lint .
```

### Dry Run (Preview Changes)

```bash
helm upgrade aiops . -n aiops --dry-run --debug
```

### View Generated Templates

```bash
helm template aiops . -n aiops
```

### Check Deployment Status

```bash
helm status aiops -n aiops
kubectl get pods -n aiops -w
```

## Advanced Usage

### Using Private Image Registry

```bash
helm install aiops . -n aiops \
  --set webhook.image=private-registry.com/aiops-webhook:latest \
  --set webhook.imagePullPolicy=Always \
  --set imagePullSecrets[0].name=regcred
```

### Enable HTTPS/TLS

```bash
helm upgrade aiops . -n aiops \
  --set ingress.tls[0].secretName=aiops-tls \
  --set ingress.tls[0].hosts[0]=grafana.example.com
```

### Resource Quotas

```bash
helm upgrade aiops . -n aiops \
  --set prometheus.resources.limits.cpu=2000m \
  --set prometheus.resources.limits.memory=2Gi
```

See [values.yaml](values.yaml) for all available options.
