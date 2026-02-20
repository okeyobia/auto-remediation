import pytest
import json
from unittest.mock import patch, MagicMock
from webhook.app import app


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
                    "labels": {"severity": "critical"},
                    "annotations": {"description": "Nginx container is down"}
                }
            ]
        }
        
        with patch('webhook.app.client') as mock_docker:
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

    def test_alert_endpoint_post_with_resolved_alert(self, client):
        """Test POST request to /alert with a resolved alert."""
        payload = {
            "alerts": [
                {
                    "status": "resolved",
                    "labels": {"severity": "critical"},
                    "annotations": {"description": "Nginx container is down"}
                }
            ]
        }
        
        with patch('webhook.app.client') as mock_docker:
            response = client.post(
                '/alert',
                data=json.dumps(payload),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            assert response.json == {"status": "processed"}
            # Should not attempt to restart on resolved alerts
            mock_docker.containers.get.assert_not_called()

    def test_alert_endpoint_post_with_multiple_alerts(self, client):
        """Test POST request with multiple alerts."""
        payload = {
            "alerts": [
                {
                    "status": "firing",
                    "labels": {"severity": "critical"},
                    "annotations": {"description": "Nginx container is down"}
                },
                {
                    "status": "resolved",
                    "labels": {"severity": "warning"},
                    "annotations": {"description": "High memory usage"}
                }
            ]
        }
        
        with patch('webhook.app.client') as mock_docker:
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
                    "labels": {"severity": "critical"},
                    "annotations": {"description": "Nginx container is down"}
                }
            ]
        }
        
        with patch('webhook.app.client') as mock_docker:
            mock_docker.containers.get.side_effect = Exception("Container not found")
            
            response = client.post(
                '/alert',
                data=json.dumps(payload),
                content_type='application/json'
            )
            
            # Should still return 200 even on error
            assert response.status_code == 200
            assert response.json == {"status": "processed"}

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
