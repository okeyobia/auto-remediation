#!/bin/bash
#
# AIOps Kubernetes Deployment Script
# Complete deployment automation for Kubernetes
#
# Usage: ./deploy-to-kubernetes.sh [kubectl|helm|skaffold]
#

set -e

NAMESPACE="aiops"
WEBHOOK_IMAGE="${WEBHOOK_IMAGE:-aiops-webhook:latest}"
DOCKER_REGISTRY="${DOCKER_REGISTRY:-}"
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ${NC}  $1"
}

log_success() {
    echo -e "${GREEN}✓${NC}  $1"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC}  $1"
}

log_error() {
    echo -e "${RED}✗${NC}  $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found. Install from: https://kubernetes.io/docs/tasks/tools/"
        exit 1
    fi
    log_success "kubectl found"

    # Check cluster access
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot access Kubernetes cluster. Check kubeconfig."
        exit 1
    fi
    log_success "Kubernetes cluster accessible"

    # Check Docker for building images
    if ! command -v docker &> /dev/null; then
        log_warn "docker not found - you'll need to build image separately"
    else
        log_success "Docker found"
    fi
}

# Build webhook Docker image
build_webhook_image() {
    log_info "Building webhook Docker image..."

    if [ -z "$DOCKER_REGISTRY" ]; then
        docker build -t "$WEBHOOK_IMAGE" ./webhook
        log_success "Built webhook image: $WEBHOOK_IMAGE"
    else
        local image="$DOCKER_REGISTRY/$WEBHOOK_IMAGE"
        docker build -t "$image" ./webhook
        docker push "$image"
        log_success "Pushed webhook image: $image"
    fi
}

# Deploy using kubectl
deploy_kubectl() {
    log_info "Deploying with kubectl..."

    # Create namespace
    log_info "Creating namespace '$NAMESPACE'..."
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
    log_success "Namespace ready"

    # Apply manifests in order
    log_info "Applying Kubernetes manifests..."
    kubectl apply -f kube/01-namespace.yaml
    kubectl apply -f kube/02-configmaps.yaml
    kubectl apply -f kube/03-secrets.yaml
    kubectl apply -f kube/04-pvcs.yaml
    kubectl apply -f kube/05-rbac.yaml
    kubectl apply -f kube/06-nginx.yaml
    kubectl apply -f kube/07-nginx-exporter.yaml
    kubectl apply -f kube/08-prometheus.yaml
    kubectl apply -f kube/09-alertmanager.yaml
    kubectl apply -f kube/10-grafana.yaml
    kubectl apply -f kube/11-webhook.yaml
    kubectl apply -f kube/12-ingress.yaml

    log_success "Manifests applied"

    # Configure Slack if provided
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        log_info "Configuring Slack webhook..."
        kubectl create secret generic slack-credentials \
            --from-literal=webhook-url="$SLACK_WEBHOOK_URL" \
            -n "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
        kubectl rollout restart deployment/webhook -n "$NAMESPACE"
        log_success "Slack configured"
    fi
}

# Deploy using Helm
deploy_helm() {
    log_info "Deploying with Helm..."

    # Check Helm
    if ! command -v helm &> /dev/null; then
        log_error "Helm not found. Install from: https://helm.sh/docs/intro/install/"
        exit 1
    fi

    local helm_values="--set webhook.image=$WEBHOOK_IMAGE"

    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        helm_values="$helm_values --set slack.enabled=true --set slack.webhookUrl=$SLACK_WEBHOOK_URL"
    fi

    helm upgrade --install aiops helm/aiops \
        -n "$NAMESPACE" --create-namespace \
        $helm_values

    log_success "Helm chart deployed"
}

# Deploy using Skaffold
deploy_skaffold() {
    log_info "Deploying with Skaffold..."

    if ! command -v skaffold &> /dev/null; then
        log_error "Skaffold not found. Install from: https://skaffold.dev/docs/install/"
        exit 1
    fi

    skaffold deploy --filename=skaffold.yaml

    log_success "Skaffold deployment complete"
}

# Wait for deployments
wait_for_deployments() {
    log_info "Waiting for deployments to be ready..."

    local deployments=(
        "nginx"
        "nginx-exporter"
        "prometheus"
        "alertmanager"
        "grafana"
        "webhook"
    )

    for deployment in "${deployments[@]}"; do
        log_info "Waiting for $deployment..."
        kubectl rollout status deployment/$deployment -n "$NAMESPACE" --timeout=5m
        log_success "$deployment ready"
    done

    log_success "All deployments ready"
}

# Show access information
show_access_info() {
    log_info "Deployment complete! 🎉"
    echo ""
    echo -e "${BLUE}Access Services:${NC}"
    echo "  Grafana:      kubectl port-forward -n $NAMESPACE svc/grafana 3000:3000"
    echo "  Prometheus:   kubectl port-forward -n $NAMESPACE svc/prometheus 9090:9090"
    echo "  AlertManager: kubectl port-forward -n $NAMESPACE svc/alertmanager 9093:9093"
    echo ""
    echo -e "${BLUE}Default Credentials:${NC}"
    echo "  Grafana: admin / admin"
    echo ""
    echo -e "${BLUE}Monitor Deployment:${NC}"
    echo "  kubectl get pods -n $NAMESPACE -w"
    echo "  kubectl logs -n $NAMESPACE -l app=webhook -f"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo "  1. Access Grafana at http://localhost:3000"
    echo "  2. Verify Prometheus is scraping metrics"
    echo "  3. Check AlertManager for configured routes"
    echo "  4. Test alert by stopping Nginx: kubectl delete pod -n $NAMESPACE -l app=nginx"
    echo ""
    echo "For detailed documentation, see: https://github.com/your-org/aiops-auto-rem/blob/main/KUBERNETES.md"
}

# Main
main() {
    local deploy_method="${1:-kubectl}"

    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════╗"
    echo "║   AIOps Kubernetes Deployment Script          ║"
    echo "╚════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""

    check_prerequisites

    if [ "$deploy_method" != "helm" ] && [ "$deploy_method" != "skaffold" ]; then
        build_webhook_image
    fi

    case "$deploy_method" in
        kubectl)
            deploy_kubectl
            ;;
        helm)
            deploy_helm
            ;;
        skaffold)
            deploy_skaffold
            ;;
        *)
            log_error "Unknown deployment method: $deploy_method"
            echo "Usage: $0 [kubectl|helm|skaffold]"
            exit 1
            ;;
    esac

    wait_for_deployments
    show_access_info
}

# Run main function
main "$@"
