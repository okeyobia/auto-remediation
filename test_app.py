import pytest
import json
from unittest.mock import patch, MagicMock
from webhook.app import app
from webhook.slack import SlackNotifier


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestWebhookAlertEndpoint:
    """Test cases for the /alert endpoint."""

    def test_alert_endpoint_post_with_firing_alert(self, client):
        """Test POST request to /alert with a firing alert."""
        payload = {
            "alerts": [
                {
                    "status": "firing",
                    "labels": {"severity": "critical", "alertname": "NginxDown"},
                    "annotations": {"description": "Nginx container is down"}
                }
            ]
        }
        
        with patch('webhook.app.client') as mock_docker:
            with patch('webhook.app.slack_notifier') as mock_slack:
                mock_container = MagicMock()
                mock_docker.containers.get.return_value = mock_container
                
                response = client.post(
                    '/alert',
                    data=json.dumps(payload),
                    content_type='application/json'
                )
                
                assert response.status_code == 200
                assert response.json == {"status": "processed"}
                mock_docker.containers.get.assert_called_once_with("nginx_app")
                mock_container.restart.assert_called_once()
                # Verify Slack notifications were sent
                assert mock_slack.send_alert.called
                assert mock_slack.send_remediation_message.called

    def test_alert_endpoint_post_with_resolved_alert(self, client):
        """Test POST request to /alert with a resolved alert."""
        payload = {
            "alerts": [
                {
                    "status": "resolved",
                    "labels": {"severity": "critical", "alertname": "NginxDown"},
                    "annotations": {"description": "Nginx container is down"}
                }
            ]
        }
        
        with patch('webhook.app.client') as mock_docker:
            with patch('webhook.app.slack_notifier') as mock_slack:
                response = client.post(
                    '/alert',
                    data=json.dumps(payload),
                    content_type='application/json'
                )
                
                assert response.status_code == 200
                assert response.json == {"status": "processed"}
                # Should not attempt to restart on resolved alerts
                mock_docker.containers.get.assert_not_called()
                # Verify Slack notification was sent for resolved alert
                mock_slack.send_alert.assert_called_once()

    def test_alert_endpoint_post_with_multiple_alerts(self, client):
        """Test POST request with multiple alerts."""
        payload = {
            "alerts": [
                {
                    "status": "firing",
                    "labels": {"severity": "critical", "alertname": "NginxDown"},
                    "annotations": {"description": "Nginx container is down"}
                },
                {
                    "status": "resolved",
                    "labels": {"severity": "warning", "alertname": "HighCPU"},
                    "annotations": {"description": "High CPU usage"}
                }
            ]
        }
        
        with patch('webhook.app.client') as mock_docker:
            with patch('webhook.app.slack_notifier') as mock_slack:
                mock_container = MagicMock()
                mock_docker.containers.get.return_value = mock_container
                
                response = client.post(
                    '/alert',
                    data=json.dumps(payload),
                    content_type='application/json'
                )
                
                assert response.status_code == 200
                # Should only restart once for the firing alert
                mock_docker.containers.get.assert_called_once()
                mock_container.restart.assert_called_once()
                # Should send Slack notifications for both alerts
                assert mock_slack.send_alert.call_count == 2

    def test_alert_endpoint_post_with_empty_alerts(self, client):
        """Test POST request with empty alerts array."""
        payload = {"alerts": []}
        
        response = client.post(
            '/alert',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        assert response.json == {"status": "processed"}

    def test_alert_endpoint_post_with_no_alerts_key(self, client):
        """Test POST request without alerts key."""
        payload = {}
        
        response = client.post(
            '/alert',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        assert response.json == {"status": "processed"}

    def test_alert_endpoint_container_restart_error(self, client):
        """Test error handling when container restart fails."""
        payload = {
            "alerts": [
                {
                    "status": "firing",
                    "labels": {"severity": "critical", "alertname": "NginxDown"},
                    "annotations": {"description": "Nginx container is down"}
                }
            ]
        }
        
        with patch('webhook.app.client') as mock_docker:
            with patch('webhook.app.slack_notifier') as mock_slack:
                mock_docker.containers.get.side_effect = Exception("Container not found")
                
                response = client.post(
                    '/alert',
                    data=json.dumps(payload),
                    content_type='application/json'
                )
                
                # Should still return 200 even on error
                assert response.status_code == 200
                assert response.json == {"status": "processed"}
                # Verify failure notification was sent
                mock_slack.send_remediation_message.assert_called_with(
                    "NginxDown", "nginx_app", success=False
                )

    def test_alert_endpoint_get_method_not_allowed(self, client):
        """Test that GET requests are not allowed."""
        response = client.get('/alert')
        assert response.status_code == 405  # Method Not Allowed

    def test_alert_endpoint_invalid_json(self, client):
        """Test POST request with invalid JSON."""
        response = client.post(
            '/alert',
            data='invalid json',
            content_type='application/json'
        )
        
        assert response.status_code == 400  # Bad Request

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get('/health')
        assert response.status_code == 200
        assert response.json["status"] == "healthy"
        assert "slack_enabled" in response.json


class TestSlackNotifier:
    """Test cases for Slack notification."""

    def test_slack_notifier_enabled_with_webhook(self):
        """Test that notifier is enabled when webhook URL is set."""
        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/services/test")
        assert notifier.enabled is True

    def test_slack_notifier_disabled_without_webhook(self):
        """Test that notifier is disabled without webhook URL."""
        notifier = SlackNotifier(webhook_url=None)
        assert notifier.enabled is False

    def test_slack_send_alert_firing(self):
        """Test sending a firing alert to Slack."""
        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/services/test")
        
        with patch('webhook.slack.requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            
            result = notifier.send_alert("NginxDown", "firing", container_name="nginx_app")
            
            assert result is True
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "https://hooks.slack.com/services/test"
            message = call_args[1]["json"]
            assert "NginxDown" in message["text"]
            assert "🚨" in message["text"]

    def test_slack_send_alert_resolved(self):
        """Test sending a resolved alert to Slack."""
        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/services/test")
        
        with patch('webhook.slack.requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            
            result = notifier.send_alert("NginxDown", "resolved")
            
            assert result is True
            message = mock_post.call_args[1]["json"]
            assert "✅" in message["text"]

    def test_slack_remediation_message_success(self):
        """Test sending remediation success message."""
        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/services/test")
        
        with patch('webhook.slack.requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            
            result = notifier.send_remediation_message("NginxDown", "nginx_app", success=True)
            
            assert result is True
            message = mock_post.call_args[1]["json"]
            assert "✓ Success" in message["text"]
            assert "0099FF" in str(message)  # Success color

    def test_slack_remediation_message_failure(self):
        """Test sending remediation failure message."""
        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/services/test")
        
        with patch('webhook.slack.requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            
            result = notifier.send_remediation_message("NginxDown", "nginx_app", success=False)
            
            assert result is True
            message = mock_post.call_args[1]["json"]
            assert "✗ Failed" in message["text"]
            assert "FF6600" in str(message)  # Failure color

    def test_slack_notifier_network_error(self):
        """Test handling of network errors."""
        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/services/test")
        
        with patch('webhook.slack.requests.post') as mock_post:
            mock_post.side_effect = Exception("Network error")
            
            result = notifier.send_alert("NginxDown", "firing")
            
            assert result is False

    def test_slack_notifier_disabled(self):
        """Test that notifier is silently disabled when no webhook URL."""
        notifier = SlackNotifier(webhook_url=None)
        
        # Should not raise exception, just return False
        result = notifier.send_alert("NginxDown", "firing")
        
        assert result is False


class TestHealthCheck:
    """Test cases for basic health check."""

    def test_app_creation(self):
        """Test that Flask app is created successfully."""
        assert app is not None
        assert app.name == 'webhook.app'

    def test_app_has_alert_route(self):
        """Test that /alert route is registered."""
        routes = [str(rule) for rule in app.url_map.iter_rules()]
        assert '/alert' in routes

    def test_app_has_health_route(self):
        """Test that /health route is registered."""
        routes = [str(rule) for rule in app.url_map.iter_rules()]
        assert '/health' in routes

