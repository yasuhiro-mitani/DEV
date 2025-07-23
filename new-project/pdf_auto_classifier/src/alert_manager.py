import requests
import json
from datetime import datetime
from typing import Dict, Any
from loguru import logger

class AlertManager:
    def __init__(self, config):
        self.config = config
        self.webhook_url = config.get('alerts.teams_webhook_url', '')
        self.enable_notifications = config.get('alerts.enable_notifications', True)
        self.notification_types = config.get('alerts.notification_types', ['error', 'warning'])
    
    def send_alert(self, message: str, alert_type: str = 'error', additional_data: Dict[str, Any] = None) -> bool:
        if not self.enable_notifications:
            logger.debug("Notifications disabled, skipping alert")
            return True
        
        if alert_type not in self.notification_types:
            logger.debug(f"Alert type '{alert_type}' not in notification types, skipping")
            return True
        
        if not self.webhook_url:
            logger.warning("No webhook URL configured, cannot send alert")
            return False
        
        try:
            payload = self._create_teams_payload(message, alert_type, additional_data)
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                logger.info(f"Alert sent successfully: {message}")
                return True
            else:
                logger.error(f"Failed to send alert, status code: {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"Error sending alert: {str(e)}")
            return False
    
    def _create_teams_payload(self, message: str, alert_type: str, additional_data: Dict[str, Any] = None) -> Dict[str, Any]:
        color = self._get_color_for_type(alert_type)
        title = f"PDF Auto Classifier - {alert_type.upper()}"
        
        facts = [
            {"name": "Time", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            {"name": "Type", "value": alert_type.upper()},
            {"name": "Message", "value": message}
        ]
        
        if additional_data:
            for key, value in additional_data.items():
                facts.append({"name": key, "value": str(value)})
        
        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": color,
            "summary": title,
            "sections": [{
                "activityTitle": title,
                "activitySubtitle": "PDF Processing Alert",
                "facts": facts,
                "markdown": True
            }]
        }
        
        return payload
    
    def _get_color_for_type(self, alert_type: str) -> str:
        color_map = {
            'error': 'FF0000',
            'warning': 'FFA500',
            'info': '0078D4',
            'success': '00FF00'
        }
        return color_map.get(alert_type.lower(), '808080')
    
    def send_processing_summary(self, total_files: int, successful: int, failed: int, errors: list) -> bool:
        if not self.enable_notifications:
            return True
        
        message = f"Processing Summary: {total_files} files processed"
        additional_data = {
            "Total Files": total_files,
            "Successful": successful,
            "Failed": failed,
            "Success Rate": f"{(successful/total_files)*100:.1f}%" if total_files > 0 else "0%"
        }
        
        if errors:
            additional_data["Recent Errors"] = "; ".join(errors[:3])
        
        alert_type = 'warning' if failed > 0 else 'info'
        
        return self.send_alert(message, alert_type, additional_data)