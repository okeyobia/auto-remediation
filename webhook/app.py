from flask import Flask, request, jsonify
import docker

app = Flask(__name__)
client = docker.from_env()


@app.route('/alert', methods=['POST'])
def alert():
    data = request.json

    for alert in data.get("alerts", []):
        if alert.get("status") == "firing":
            container_name = "nginx_app"
            try:
                container = client.containers.get(container_name)
                container.restart()
                print(f"Restarted {container_name}")
            except Exception as e:
                print(f"Error restarting container: {e}")

    return jsonify({"status": "processed"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)