from flask import Flask, request, jsonify
import docker
import os
from slack import SlackNotifier

app = Flask(__name__)
client = docker.from_env()
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
                
                container_name = "nginx_app"
                try:
                    container = client.containers.get(container_name)
                    container.restart()
                    print(f"Restarted {container_name} due to Grafana alert: {alert_name}")
                    
                    # Send remediation success notification
                    slack_notifier.send_remediation_message(alert_name, container_name, success=True)
                except Exception as e:
                    print(f"Error restarting container: {e}")
                    
                    # Send remediation failure notification
                    slack_notifier.send_remediation_message(alert_name, container_name, success=False)
            
            # Send Slack notification for alert resolved
            elif alert_status == "resolved":
                slack_notifier.send_alert(alert_name, alert_status)
                print(f"Alert resolved: {alert_name}")
    
    # Handle Prometheus alert manager format (legacy)
    elif "alerts" in data:
        for alert in data.get("alerts", []):
            if alert.get("status") == "firing":
                alert_name = alert.get("labels", {}).get("alertname", "unknown")
                
                # Send Slack notification
                slack_notifier.send_alert(alert_name, "firing")
                
                container_name = "nginx_app"
                try:
                    container = client.containers.get(container_name)
                    container.restart()
                    print(f"Restarted {container_name}")
                    
                    # Send remediation success notification
                    slack_notifier.send_remediation_message(alert_name, container_name, success=True)
                except Exception as e:
                    print(f"Error restarting container: {e}")
                    
                    # Send remediation failure notification
                    slack_notifier.send_remediation_message(alert_name, container_name, success=False)

    return jsonify({"status": "processed"})


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "slack_enabled": slack_notifier.enabled})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

