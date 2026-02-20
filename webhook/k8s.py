"""Kubernetes API client for pod/deployment restarts."""

import os
import logging
from datetime import datetime, timedelta

try:
    from kubernetes import client, config, watch
    K8S_AVAILABLE = True
except ImportError:
    K8S_AVAILABLE = False

logger = logging.getLogger(__name__)


class KubernetesRemediator:
    """Handle remediation actions using Kubernetes API."""

    def __init__(self):
        """Initialize Kubernetes client."""
        self.enabled = K8S_AVAILABLE and self._load_config()
        self.v1 = None
        self.apps_v1 = None
        self.namespace = os.getenv("POD_NAMESPACE", "aiops")

        if self.enabled:
            try:
                self.v1 = client.CoreV1Api()
                self.apps_v1 = client.AppsV1Api()
                logger.info(f"✓ Kubernetes client initialized for namespace: {self.namespace}")
            except Exception as e:
                logger.error(f"Failed to initialize Kubernetes client: {e}")
                self.enabled = False

    def _load_config(self):
        """Load Kubernetes config (in-cluster or kubeconfig)."""
        try:
            # Try in-cluster config first
            config.load_incluster_config()
            return True
        except Exception:
            try:
                # Fall back to kubeconfig
                config.load_kube_config()
                return True
            except Exception:
                logger.warning("Could not load Kubernetes config")
                return False

    def trigger_deployment_restart(self, deployment_name):
        """Restart a deployment by triggering a rolling restart.
        
        This works by adding an annotation to the deployment spec,
        which causes Kubernetes to recreate the pods.
        """
        if not self.enabled:
            logger.warning("Kubernetes client not available")
            return False, "Kubernetes client not available"

        try:
            deployment = self.apps_v1.read_namespaced_deployment(
                deployment_name, self.namespace
            )

            # Add restart timestamp annotation to force pod recreation
            if deployment.spec.template.metadata.annotations is None:
                deployment.spec.template.metadata.annotations = {}

            deployment.spec.template.metadata.annotations[
                "restartTimestamp"
            ] = datetime.utcnow().isoformat()

            # Apply the updated deployment
            self.apps_v1.patch_namespaced_deployment(
                deployment_name, self.namespace, deployment
            )

            logger.info(f"✓ Triggered restart for deployment: {deployment_name}")
            return True, f"Successfully triggered restart for {deployment_name}"

        except client.rest.ApiException as e:
            error_msg = f"Kubernetes API error: {e.status} {e.reason}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Failed to restart deployment {deployment_name}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def scale_deployment(self, deployment_name, replicas=1):
        """Scale a deployment to specified number of replicas."""
        if not self.enabled:
            logger.warning("Kubernetes client not available")
            return False, "Kubernetes client not available"

        try:
            deployment = self.apps_v1.read_namespaced_deployment(
                deployment_name, self.namespace
            )
            deployment.spec.replicas = replicas
            self.apps_v1.patch_namespaced_deployment(
                deployment_name, self.namespace, deployment
            )

            logger.info(f"✓ Scaled {deployment_name} to {replicas} replicas")
            return True, f"Successfully scaled {deployment_name} to {replicas} replicas"

        except client.rest.ApiException as e:
            error_msg = f"Kubernetes API error: {e.status} {e.reason}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Failed to scale deployment {deployment_name}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def get_deployment_status(self, deployment_name):
        """Get deployment status."""
        if not self.enabled:
            return None

        try:
            deployment = self.apps_v1.read_namespaced_deployment(
                deployment_name, self.namespace
            )
            return {
                "name": deployment_name,
                "replicas": deployment.status.replicas,
                "ready_replicas": deployment.status.ready_replicas,
                "conditions": [
                    {
                        "type": c.type,
                        "status": c.status,
                        "message": c.message,
                    }
                    for c in (deployment.status.conditions or [])
                ],
            }
        except Exception as e:
            logger.error(f"Failed to get deployment status: {e}")
            return None
