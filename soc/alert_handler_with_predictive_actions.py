"""Alert Handler with Predictive Actions Integration.

Handles security alerts and CI failures with intelligent action recommendations.
Integrates with ci-failure-agent predictive actions REST API.
"""

import aiohttp
import logging
import json
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    """Security or CI alert data structure."""
    alert_id: str
    alert_type: str  # security_alert, ci_failure, spam_incident
    severity: str  # critical, high, medium, low
    title: str
    description: str
    source: str
    timestamp: str
    context: Dict = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class RecommendedAction:
    """Action recommendation from predictive API."""
    action_id: str
    title: str
    description: str
    action_type: str
    priority: int
    estimated_time: Optional[str] = None
    success_rate: Optional[float] = None


class AlertHandlerWithPredictiveActions:
    """Handle alerts with predictive action recommendations."""
    
    def __init__(self, 
                 predictive_api_url: str = "http://ci-agent:8000",
                 timeout: int = 10):
        """Initialize alert handler.
        
        Args:
            predictive_api_url: URL of predictive actions API
            timeout: Request timeout in seconds
        """
        self.api_url = predictive_api_url
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
        self.action_logs: List[Dict] = []
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def handle_alert(self, alert: Alert) -> Dict:
        """Process alert and get predictive action recommendations.
        
        Args:
            alert: Alert object with details
            
        Returns:
            Dictionary with recommendations and metadata
        """
        try:
            logger.info(f"Processing alert {alert.alert_id}: {alert.alert_type}")
            
            # Map alert type to failure type for API
            failure_type_map = {
                "security_alert": "security_alert",
                "ci_failure": "ci_failure",
                "spam_incident": "spam_incident"
            }
            failure_type = failure_type_map.get(alert.alert_type, "security_alert")
            
            # Call predictive actions API
            recommendations = await self._get_predictive_actions(
                failure_description=alert.description,
                failure_type=failure_type,
                context=alert.context or {},
                severity=alert.severity,
                user_id=alert.user_id,
                session_id=alert.session_id
            )
            
            # Create response with UI-ready format
            response = {
                "alert_id": alert.alert_id,
                "alert_type": alert.alert_type,
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": recommendations["request_id"],
                "actions": self._format_actions_for_ui(
                    recommendations["actions"],
                    recommendations["recommended_action_id"]
                ),
                "notification": self._create_notification(alert, recommendations),
                "status": "ready_for_action"
            }
            
            logger.info(f"Alert processed successfully with {len(response['actions'])} recommendations")
            return response
            
        except Exception as e:
            logger.error(f"Error handling alert: {str(e)}")
            return {
                "alert_id": alert.alert_id,
                "status": "error",
                "error": str(e)
            }
    
    async def _get_predictive_actions(self,
                                      failure_description: str,
                                      failure_type: str,
                                      context: Dict,
                                      severity: str,
                                      user_id: Optional[str],
                                      session_id: Optional[str]) -> Dict:
        """Call predictive actions API endpoint."""
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        url = f"{self.api_url}/api/predictive_actions"
        payload = {
            "failure_description": failure_description,
            "failure_type": failure_type,
            "context": context,
            "severity": severity,
            "user_id": user_id,
            "session_id": session_id
        }
        
        async with self.session.post(url, json=payload) as response:
            if response.status != 200:
                raise Exception(f"API error: {response.status}")
            return await response.json()
    
    def _format_actions_for_ui(self, actions: List[Dict], 
                               recommended_id: Optional[str]) -> List[Dict]:
        """Format actions for UI display."""
        formatted = []
        for idx, action in enumerate(actions):
            is_recommended = action["action_id"] == recommended_id
            
            ui_action = {
                "id": action["action_id"],
                "title": action["title"],
                "description": action["description"],
                "type": action["action_type"],
                "priority": action["priority"],
                "estimated_time": action.get("estimated_time", "Unknown"),
                "confidence": round((action.get("success_rate", 0) or 0) * 100),
                "is_recommended": is_recommended,
                "button_label": self._get_button_label(action["action_type"]),
                "icon": self._get_icon(action["action_type"])
            }
            formatted.append(ui_action)
        
        return formatted
    
    def _get_button_label(self, action_type: str) -> str:
        """Get UI button label for action type."""
        labels = {
            "auto_fix": "Execute Fix",
            "manual_review": "Review Details",
            "escalate": "Escalate",
            "ignore": "Dismiss"
        }
        return labels.get(action_type, "Action")
    
    def _get_icon(self, action_type: str) -> str:
        """Get UI icon for action type."""
        icons = {
            "auto_fix": "🔧",
            "manual_review": "👁",
            "escalate": "⚠",
            "ignore": "✓"
        }
        return icons.get(action_type, "➤")
    
    def _create_notification(self, alert: Alert, recommendations: Dict) -> Dict:
        """Create notification for alert."""
        severity_colors = {
            "critical": "#ff0000",
            "high": "#ff6600",
            "medium": "#ffaa00",
            "low": "#00aa00"
        }
        
        return {
            "title": alert.title,
            "message": alert.description,
            "severity": alert.severity,
            "color": severity_colors.get(alert.severity, "#cccccc"),
            "action_count": len(recommendations["actions"]),
            "recommended_action": recommendations.get("recommended_action_id")
        }
    
    async def log_user_action(self, request_id: str, action_id: str,
                              outcome: Optional[str] = None,
                              feedback: Optional[str] = None) -> Dict:
        """Log user's action selection to API for ML training.
        
        Args:
            request_id: Original request ID
            action_id: Selected action ID
            outcome: Result (successful, failed, partial)
            feedback: User feedback
            
        Returns:
            Confirmation response
        """
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        try:
            url = f"{self.api_url}/api/actions/log_selection"
            payload = {
                "request_id": request_id,
                "action_id": action_id,
                "selected_at": datetime.utcnow().isoformat(),
                "outcome": outcome,
                "feedback": feedback
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status != 200:
                    logger.error(f"Logging failed: {response.status}")
                    return {"status": "error"}
                
                result = await response.json()
                self.action_logs.append(result)
                logger.info(f"Action selection logged: {action_id}")
                return result
                
        except Exception as e:
            logger.error(f"Error logging action: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def get_logs(self) -> List[Dict]:
        """Get local action logs."""
        return self.action_logs


# Example usage
async def example_alert_handling():
    """Example of handling an alert with predictive actions."""
    alert = Alert(
        alert_id="alert-001",
        alert_type="security_alert",
        severity="high",
        title="Suspicious Login Attempt",
        description="Multiple failed login attempts from unknown IP address",
        source="auth-system",
        timestamp=datetime.utcnow().isoformat(),
        context={"ip": "192.168.1.100", "attempts": 5},
        user_id="analyst@example.com"
    )
    
    async with AlertHandlerWithPredictiveActions() as handler:
        # Handle alert and get recommendations
        result = await handler.handle_alert(alert)
        print(json.dumps(result, indent=2))
        
        # Simulate user selecting an action
        if "actions" in result and result["actions"]:
            selected_action = result["actions"][0]
            log_result = await handler.log_user_action(
                request_id=result["request_id"],
                action_id=selected_action["id"],
                outcome="successful",
                feedback="Action quickly resolved the issue"
            )
            print(f"\nLogged: {log_result}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(example_alert_handling())
