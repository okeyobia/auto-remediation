# Kubernetes Deployment Guide

Deploy the AIOps auto-remediation system to Kubernetes.

## Prerequisites

- Kubernetes cluster (1.20+)
- kubectl configured to access your cluster
- Docker registry access or local Docker daemon for building images
- Optional: Helm (for advanced deployments)
- Optional: cert-manager (for HTTPS with Ingress)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Kubernetes Cluster                 │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────┐      ┌──────────────┐                    │
│  │  Nginx   │◄─────┤ Nginx        │                    │
│  │ (app)    │      │ Exporter     │                    │
│  └────┬─────┘      └──────┬───────┘                    │
│       │                     │ :9113                      │
│       │                     │                            │
│       └─────────────────────┼────────┐                  │
│                             │        │                  │
│                       ┌─────▼────────▼────┐             │
│                       │   Prometheus      │             │
│                       │  :9090            │             │
│                       └─────┬─────────────┘             │
│                             │                           │
│               ┌─────────────┼─────────────┐             │
│               │             │             │             │
│          ┌────▼───┐  ┌────────────┐  ┌────▼──────┐    │
│          │AlertMgr│  │ Grafana    │  │  Webhook  │    │
│          │:9093   │  │ :3000      │  │ :5000     │    │
│          └────┬───┘  └────────────┘  └────┬──────┘    │
│               │                           │             │
│               │        Ingress            │             │
│               └────────────┬──────────────┘             │
│                            │                            │
│      ┌──────────────────────┼──────────────────┐        │
│      ▼                      ▼                  ▼        │
│ alertmgr.*.local   grafana.*.local   webhook (internal)│
│                                                           │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Build Webhook Docker Image

```bash
# Build the webhook image locally or push to registry
docker build -t aiops-webhook:latest ./webhook

# If using a registry (Docker Hub, ECR, GCR, etc):
docker tag aiops-webhook:latest your-registry/aiops-webhook:latest
docker push your-registry/aiops-webhook:latest
```

### 2. Create Kubernetes Resources

Apply manifests in order:

```bash
# Create namespace
kubectl apply -f kube/01-namespace.yaml

# Create configuration
kubectl apply -f kube/02-configmaps.yaml

# Configure Slack webhook URL (optional)
# Edit the secret with your Slack webhook URL
kubectl apply -f kube/03-secrets.yaml

# Create persistent volumes
kubectl apply -f kube/04-pvcs.yaml

# Setup RBAC for webhook
kubectl apply -f kube/05-rbac.yaml

# Deploy services (order matters - dependencies)
kubectl apply -f kube/06-nginx.yaml
kubectl apply -f kube/07-nginx-exporter.yaml
kubectl apply -f kube/08-prometheus.yaml
kubectl apply -f kube/09-alertmanager.yaml
kubectl apply -f kube/10-grafana.yaml
kubectl apply -f kube/11-webhook.yaml

# Setup ingress for external access
kubectl apply -f kube/12-ingress.yaml
```

Or apply all at once (if in correct dependency order):

```bash
kubectl apply -f kube/
```

### 3. Verify Deployment

```bash
# Check all pods are running
kubectl get pods -n aiops
kubectl get svc -n aiops
kubectl get ingress -n aiops

# View logs
kubectl logs -n aiops -l app=webhook -f
kubectl logs -n aiops -l app=grafana -f
```

## Configuration

### Slack Integration

To enable Slack notifications:

```bash
# Create secret with Slack webhook URL
kubectl create secret generic slack-credentials \
  --from-literal=webhook-url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL" \
  -n aiops \
  --dry-run=client -o yaml | kubectl apply -f -
```

Or edit [03-secrets.yaml](03-secrets.yaml) directly:

```yaml
stringData:
  webhook-url: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

### Custom Alert Rules

Edit [02-configmaps.yaml](02-configmaps.yaml) to add new alert rules in the `alert_rules.yml` section:

```yaml
- alert: CustomAlert
  expr: your_metric > threshold
  for: 5m
  labels:
    severity: warning
  annotations:
    description: "Alert description"
```

Then reload Prometheus:

```bash
kubectl rollout restart deployment/prometheus -n aiops
```

### Scaling

Scale deployments as needed:

```bash
# Scale nginx to 3 replicas
kubectl scale deployment nginx --replicas=3 -n aiops

# Scale webhook to 3 for high availability
kubectl scale deployment webhook --replicas=3 -n aiops

# Auto-scale with HPA (requires metrics-server)
kubectl autoscale deployment nginx --min=2 --max=5 -n aiops
```

## Access Services

### Port Forwarding (Local Development)

```bash
# Grafana
kubectl port-forward -n aiops svc/grafana 3000:3000

# Prometheus
kubectl port-forward -n aiops svc/prometheus 9090:9090

# AlertManager
kubectl port-forward -n aiops svc/alertmanager 9093:9093
```

### Via Ingress (Cluster Access)

Add to your `/etc/hosts` (or for cloud clusters, use LoadBalancer):

```
<ingress-ip> grafana.aiops.local prometheus.aiops.local alertmanager.aiops.local nginx.aiops.local
```

Or use NodePort to access services directly.

## Webhook Remediation in Kubernetes

The webhook uses Kubernetes API to restart deployments when alerts fire:

### Alert Triggers Deployment Restart

When `NginxDown` alert fires:

```
Alert → WebHook Service → Kubernetes API → Rolling Restart of Nginx Deployment
```

### Deployment Restart Mechanism

The webhook patches deployments with a `restartTimestamp` annotation, causing Kubernetes to automatically restart pods:

```yaml
spec:
  template:
    metadata:
      annotations:
        restartTimestamp: "2024-02-19T14:23:45"
```

This is a graceful, Kubernetes-native way to restart services.

### Custom Remediation Actions

Edit webhook app.py to define remediation for different alerts:

```python
if alert_name == "NginxDown":
    success, message = k8s_remediator.trigger_deployment_restart("nginx")
elif alert_name == "HighMemory":
    success, message = k8s_remediator.scale_deployment("nginx", replicas=3)
```

## Monitoring Deployment Health

### View Pod Status

```bash
kubectl describe pod -n aiops <pod-name>
kubectl logs -n aiops <pod-name>
```

### Check Webhook Readiness

```bash
kubectl get deployment webhook -n aiops -o wide
kubectl rollout status deployment/webhook -n aiops
```

### Monitor Storage

```bash
kubectl get pvc -n aiops
kubectl describe pvc prometheus-data -n aiops
```

## Troubleshooting

### Pods not starting

```bash
# Check pod events
kubectl describe pod webhook-xxx -n aiops

# Check image availability
kubectl get events -n aiops --sort-by='.lastTimestamp'
```

### Metrics not collecting

```bash
# Verify Prometheus is scraping
kubectl port-forward -n aiops svc/prometheus 9090:9090
# Visit http://localhost:9090/targets

# Check AlertManager connectivity
kubectl logs -n aiops deployment/prometheus | grep alertmanager
```

### Slack notifications not sending

```bash
# Check secret is set
kubectl get secret slack-credentials -n aiops -o yaml

# Verify webhook logs
kubectl logs -n aiops deployment/webhook | grep -i slack
```

### Storage Issues

```bash
# Check PVC status
kubectl get pvc -n aiops

# Increase storage if needed
kubectl patch pvc prometheus-data -n aiops -p '{"spec":{"resources":{"requests":{"storage":"20Gi"}}}}'
```

## Production Considerations

### High Availability

- Set `replicas: 3` for each deployment
- Use PodDisruptionBudgets (included in webhook)
- Configure node affinity for multi-node setups

### Resource Limits

Adjust resource requests/limits in manifests based on your cluster capacity:

```yaml
resources:
  requests:
    cpu: 500m
    memory: 1Gi
  limits:
    cpu: 2000m
    memory: 2Gi
```

### Persistent Storage

- Use appropriate storage classes for your cloud provider (AWS EBS, GCP Persistent Disk, etc.)
- Consider backup solutions for Prometheus and Grafana data
- Monitor storage growth with: `kubectl get pvc -n aiops -w`

### Security

- Use NetworkPolicies to restrict traffic
- Enable Pod Security Policies/Standards
- Rotate Slack webhook secrets regularly
- Use service accounts with minimal required permissions (RBAC is configured)

### Monitoring Setup

- Enable persistent Prometheus storage (already configured)
- Setup Grafana alerts (see main README)
- Configure log aggregation (ELK, Splunk, etc.)

## Cleanup

Remove all AIOps resources:

```bash
# Remove all resources
kubectl delete namespace aiops

# Or delete individual components
kubectl delete -f kube/ -n aiops
```

## Next Steps

1. Access Grafana at http://grafana.aiops.local (default: admin/admin)
2. Configure additional dashboards in Grafana UI
3. Define custom alert rules for your services
4. Setup TLS with cert-manager for production
5. Configure persistent backups for data

See main [README.md](../README.md) for more information about the AIOps system.
