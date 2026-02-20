from flask import Flask, request, jsonify
import docker
import os

app = Flask(__name__)
client = docker.from_env()


@app.route('/alert', methods=['POST'])
def alert():
    data = request.json
    
    # Handle Grafana alert format
    if "alerts" in data and isinstance(data["alerts"], list):
        # Grafana format
        for alert in data.get("alerts", []):
            if alert.get("status") == "firing":
                container_name = "nginx_app"
                try:
                    container = client.containers.get(container_name)
                    container.restart()
                    print(f"Restarted {container_name} due to Grafana alert: {alert.get('labels', {}).get('alertname', 'unknown')}")
                except Exception as e:
                    print(f"Error restarting container: {e}")
    
    # Handle Prometheus alert manager format (legacy)
    elif "alerts" in data:
        for alert in data.get("alerts", []):
            if alert.get("status") == "firing":
                container_name = "nginx_app"
                try:
                    container = client.containers.get(container_name)
                    container.restart()
                    print(f"Restarted {container_name} due to Prometheus alert")
                except Exception as e:
                    print(f"Error restarting container: {e}")

    return jsonify({"status": "processed"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
