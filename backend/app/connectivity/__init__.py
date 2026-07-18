"""
NovaFlow Enterprise Connectivity Platform (ECP).

Permanent integration backbone — all external operations flow through this platform.
"""

from app.connectivity.integration import invoke_connector_action, send_notification, test_connection
from app.connectivity.registry import list_connectors

__all__ = [
    "list_connectors",
    "invoke_connector_action",
    "send_notification",
    "test_connection",
]
