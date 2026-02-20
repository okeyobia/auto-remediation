from flask import Flask, request, jsonify
import os
import logging
from slack import SlackNotifier
from k8s import KubernetesRemediator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Try to initialize Docker client (for Docker Compose environments)
try:
    import docker
    docker_client = docker.from_env()
    docker_available = True
    logger.info("✓ Docker client initialized")
except Exception as e:
    docker_client = None
    docker_available = False
    logger.info(f"ℹ Docker not available: {e}")

# Initialize Kubernetes remediator
k8s_remediator = KubernetesRemediator()

# Initialize Slack notifier
slack_notifier = SlackNotifier()


@app.route('/alert', methods=['POST'])
def alert():
    data = request.json
    
    # Handle Grafana alert format
    if "alerts" in data and isinstance(data["alerts"], list):
        # Grafana format
        for alert in data.get("alerts", []):
            alert_name = alert.get("labels", {}).get("alertname", "unknown")
            alert_status = alert.get("status", "unknown")
            
            # Send Slack notification for alert firing
            if alert_status == "firing":
                slack_notifier.send_alert(alert_name, alert_status)
                
                # Trigger remediation based on available platform
                success, message = trigger_remediation(alert_name)
                
                # Send remediation notification
                slack_notifier.send_remediation_message(
                    alert_name, 
                    "nginx_app", 
                    success=success
                )
                
                logger.info(f"{'✓' if success else '✗'} {message}")
            
            # Send Slack notification for alert resolved
            elif alert_status == "resolved":
                slack_notifier.send_alert(alert_name, alert_status)
                logger.info(f"Alert resolved: {alert_name}")
    
    # Handle Prometheus alert manager format (legacy)
    elif "alerts" in data:
        for alert in data.get("alerts", []):
            if alert.get("status") == "firing":
                alert_name = alert.get("labels", {}).get("alertname", "unknown")
                
                # Send Slack notification
                slack_notifier.send_alert(alert_name, "firing")
                
                # Trigger remediation
                success, message = trigger_remediation(alert_name)
                
                # Send remediation notification
                slack_notifier.send_remediation_message(
                    alert_name, 
                    "nginx_app", 
                    success=success
                )
                
                logger.info(f"{'✓' if success else '✗'} {message}")

    return jsonify({"status": "processed"})


def trigger_remediation(alert_name):
    """Trigger remediation based on alert name.
    
    Returns: (success: bool, message: str)
    """
    if alert_name == "NginxDown":
        # Try Kubernetes first, fall back to Docker
        if k8s_remediator.enabled:
            success, message = k8s_remediator.trigger_deployment_restart("nginx")
            return success, message
        elif docker_available:
            try:
                container = docker_client.containers.get("nginx_app")
                container.restart()
                return True, f"Restarted container nginx_app"
            except Exception as e:
                return False, f"Error restarting container: {e}"
        else:
            return False, "No remediation platform available (no Docker socket, no K8s API)"
    
    return False, f"Unknown alert: {alert_name}"


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "slack_enabled": slack_notifier.enabled,
        "docker_available": docker_available,
        "kubernetes_available": k8s_remediator.enabled
    })


if __name__ == "__main__":
    logger.info("Starting AIOps webhook service")
    logger.info(f"Docker: {'✓ Available' if docker_available else '✗ Not available'}")
    logger.info(f"Kubernetes: {'✓ Available' if k8s_remediator.enabled else '✗ Not available'}")
    logger.info(f"Slack: {'✓ Enabled' if slack_notifier.enabled else '✗ Disabled'}")
    app.run(host="0.0.0.0", port=5000, debug=False)


