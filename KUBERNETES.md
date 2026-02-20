# Kubernetes Deployment Quick Reference

## What Was Added

### 1. Kubernetes Manifests (`kube/` directory)
- **01-namespace.yaml** - Creates `aiops` namespace
- **02-configmaps.yaml** - Configuration for Prometheus, AlertManager, Nginx, Grafana
- **03-secrets.yaml** - Slack webhook credentials (needs your actual URL)
- **04-pvcs.yaml** - Persistent storage for Prometheus & Grafana
- **05-rbac.yaml** - ServiceAccount and Role for webhook to access Kubernetes API
- **06-nginx.yaml** - Nginx deployment (2 replicas) + Service
- **07-nginx-exporter.yaml** - Nginx Prometheus exporter deployment + Service
- **08-prometheus.yaml** - Prometheus deployment + Service
- **09-alertmanager.yaml** - AlertManager deployment + Service
- **10-grafana.yaml** - Grafana deployment (persistent storage) + Service
- **11-webhook.yaml** - Webhook deployment (2 replicas, HA) + Service + PDB
- **12-ingress.yaml** - Ingress for external HTTP routing

### 2. Webhook Kubernetes Module (`webhook/k8s.py`)
- `KubernetesRemediator` class for triggering pod restarts
- Automatic in-cluster and kubeconfig authentication
- Graceful pod restart via deployment annotation patching
- Deployment scaling capabilities
- Status queries for debugging

### 3. Helm Chart (`helm/aiops/`)
- **Chart.yaml** - Chart metadata
- **values.yaml** - All configurable parameters
- **README.md** - Helm-specific deployment guide

### 4. Skaffold Configuration (`skaffold.yaml`)
- Local Kubernetes development setup
- Auto-build webhook image
- Auto-deploy to cluster
- Port forwarding for services

### 5. Updated Documentation
- **kube/README.md** - Comprehensive Kubernetes guide
- **helm/aiops/README.md** - Helm chart usage guide
- Main **README.md** - Added Kubernetes deployment section

---

## Quick Start

### Option 1: Using kubectl (Direct manifests)

```bash
# 1. Build webhook image
docker build -t aiops-webhook:latest ./webhook

# 2. Deploy to Kubernetes
kubectl apply -f kube/

# 3. Set Slack webhook (optional)
kubectl create secret generic slack-credentials \
  --from-literal=webhook-url="https://hooks.slack.com/services/..." \
  -n aiops --dry-run=client -o yaml | kubectl apply -f -

# 4. Access services
kubectl port-forward -n aiops svc/grafana 3000:3000
kubectl port-forward -n aiops svc/prometheus 9090:9090
```

### Option 2: Using Helm (Recommended)

```bash
# 1. Build webhook image
docker build -t aiops-webhook:latest ./webhook

# 2. Install Helm chart
helm install aiops helm/aiops -n aiops --create-namespace \
  --set webhook.image=aiops-webhook:latest

# 3. Access services
helm status aiops -n aiops
kubectl port-forward -n aiops svc/grafana 3000:3000
```

### Option 3: Using Skaffold (Local development)

```bash
# 1. Install Skaffold: https://skaffold.dev/docs/install/

# 2. Deploy to local K8s cluster (Docker Desktop, Minikube, etc.)
skaffold dev

# This auto-builds webhook image and forwards ports automatically
```

---

## Kubernetes Architecture

```
┌──────────────────────────────────────────────┐
│         Kubernetes Cluster (aiops NS)        │
├──────────────────────────────────────────────┤
│                                               │
│  Nginx (2 pods) ─┐                          │
│      ▼           │                          │
│  Nginx Exporter  │  ─────────────┐          │
│                  │               │          │
│              Prometheus ◄────────┘          │
│                  │                          │
│  Grafana ◄───────┘                         │
│      │                                      │
│      ├──> AlertManager                     │
│      │        │                             │
│      └─────────└──> Webhook (2 pods) ●    │
│                     (restarts pods)        │
│                                               │
│  Persistent Storage:                        │
│  ├─ Prometheus: 10Gi (metrics)             │
│  └─ Grafana: 5Gi (dashboards)              │
│                                               │
└──────────────────────────────────────────────┘
```

---

## Key Differences from Docker Compose

| Feature | Docker Compose | Kubernetes |
|---------|----------------|-----------|
| **Container Restart** | Docker API via socket | Kubernetes API (native) |
| **Pod Restart Method** | Direct container restart | Deployment annotation patch (graceful) |
| **High Availability** | Manual multi-host setup | Built-in (2-3 replicas) |
| **Persistent Storage** | Docker volumes | PersistentVolumeClaims |
| **Configuration** | Env vars + files | ConfigMaps + Secrets |
| **Networking** | Docker network | Kubernetes Services |
| **Scaling** | Manual | Horizontal Pod Autoscaler (HPA) |
| **Load Balancing** | Nginx/external | Kubernetes Service |
| **RBAC** | N/A | Full ServiceAccount + Role/RoleBinding |

---

## Accessing Services

### Local Development (Port Forwarding)
```bash
# Grafana Dashboard
kubectl port-forward -n aiops svc/grafana 3000:3000
# Visit: http://localhost:3000 (admin/admin)

# Prometheus
kubectl port-forward -n aiops svc/prometheus 9090:9090
# Visit: http://localhost:9090

# AlertManager
kubectl port-forward -n aiops svc/alertmanager 9093:9093
# Visit: http://localhost:9093
```

### Production (Ingress)
```bash
# Edit /etc/hosts (or configure DNS)
<ingress-ip> grafana.aiops.local prometheus.aiops.local alertmanager.aiops.local

# Or use NodePort (edit 12-ingress.yaml)
```

---

## Remediation Flow (Kubernetes)

```
Alert Fires (e.g., Nginx Down)
    ▼
Grafana Evaluates Alert Rule
    ▼
Webhook Receives HTTP POST from Grafana
    ▼
Webhook Creates KubernetesRemediator
    ▼
KubernetesRemediator Patches Nginx Deployment
    ├─ Adds/updates 'restartTimestamp' annotation
    └─ Triggers automatic pod recreation
    ▼
Kubernetes Recreates Nginx Pods (rolling restart)
    ▼
Slack Notification Sent (if configured)
    ├─ Alert Firing: 🚨
    ├─ Remediation Success: ✓
    └─ Resolved: ✅
```

---

## Configuration & Customization

### Add New Alert Rules
Edit `kube/02-configmaps.yaml`:
```yaml
- alert: CustomAlert
  expr: your_metric > threshold
  for: 5m
  annotations:
    description: "Your custom alert"
```

Then: `kubectl rollout restart deployment/prometheus -n aiops`

### Scale Services
```bash
kubectl scale deployment nginx --replicas=5 -n aiops
kubectl scale deployment webhook --replicas=3 -n aiops
kubectl autoscale deployment grafana --min=1 --max=3 -n aiops
```

### Change Slack Webhook
```bash
kubectl patch secret slack-credentials -n aiops -p \
  '{"data":{"webhook-url":"'$(echo -n "https://hooks.slack.com/services/..." | base64)'"}}'
```

### Update Container Images
```bash
kubectl set image deployment/webhook webhook=your-registry/aiops-webhook:v2 -n aiops
```

---

## Troubleshooting

### Check Pod Status
```bash
kubectl get pods -n aiops
kubectl describe pod <pod-name> -n aiops
kubectl logs <pod-name> -n aiops
```

### Verify Remediation RBAC
```bash
kubectl auth can-i patch deployments --as=system:serviceaccount:aiops:webhook -n aiops
```

### Check Slack Configuration
```bash
kubectl get secret slack-credentials -n aiops -o jsonpath='{.data.webhook-url}' | base64 -d
```

### Verify Alert Routing
```bash
kubectl port-forward -n aiops svc/prometheus 9090:9090
# Visit http://localhost:9090/alerts - check "NginxDown" rule status
```

---

## Next Steps

1. **Review Kubernetes architecture** - See [kube/README.md](../kube/README.md)
2. **Configure Slack** - Get webhook URL from Slack API section
3. **Customize alert rules** - Edit ConfigMap in manifests
4. **Setup TLS/HTTPS** - Install cert-manager for Ingress
5. **Monitor autoscaling** - Use HPA for dynamic scaling

---

See [kube/README.md](../kube/README.md) and [helm/aiops/README.md](../helm/aiops/README.md) for comprehensive documentation.
