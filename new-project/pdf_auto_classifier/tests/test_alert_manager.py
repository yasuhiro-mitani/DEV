import unittest
from unittest.mock import Mock, patch, MagicMock
from src.alert_manager import AlertManager

class TestAlertManager(unittest.TestCase):
    def setUp(self):
        self.config = Mock()
        self.config.get.side_effect = lambda key, default=None: {
            'alerts.teams_webhook_url': 'https://test.webhook.url',
            'alerts.enable_notifications': True,
            'alerts.notification_types': ['error', 'warning']
        }.get(key, default)
        
        self.alert_manager = AlertManager(self.config)
    
    def test_send_alert_success(self):
        with patch('src.alert_manager.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            result = self.alert_manager.send_alert("Test message", "error")
            
            self.assertTrue(result)
            mock_post.assert_called_once()
    
    def test_send_alert_disabled(self):
        self.alert_manager.enable_notifications = False
        
        result = self.alert_manager.send_alert("Test message", "error")
        
        self.assertTrue(result)
    
    def test_send_alert_wrong_type(self):
        result = self.alert_manager.send_alert("Test message", "info")
        
        self.assertTrue(result)
    
    def test_send_alert_no_webhook(self):
        self.alert_manager.webhook_url = ""
        
        result = self.alert_manager.send_alert("Test message", "error")
        
        self.assertFalse(result)
    
    def test_create_teams_payload(self):
        payload = self.alert_manager._create_teams_payload(
            "Test message", 
            "error", 
            {"file": "test.pdf"}
        )
        
        self.assertEqual(payload["@type"], "MessageCard")
        self.assertEqual(payload["themeColor"], "FF0000")
        self.assertIn("sections", payload)
        self.assertEqual(len(payload["sections"][0]["facts"]), 4)
    
    def test_get_color_for_type(self):
        test_cases = [
            ("error", "FF0000"),
            ("warning", "FFA500"),
            ("info", "0078D4"),
            ("success", "00FF00"),
            ("unknown", "808080")
        ]
        
        for alert_type, expected_color in test_cases:
            with self.subTest(alert_type=alert_type):
                result = self.alert_manager._get_color_for_type(alert_type)
                self.assertEqual(result, expected_color)
    
    def test_send_processing_summary(self):
        with patch.object(self.alert_manager, 'send_alert') as mock_send:
            mock_send.return_value = True
            
            result = self.alert_manager.send_processing_summary(
                total_files=10, 
                successful=8, 
                failed=2, 
                errors=["Error 1", "Error 2"]
            )
            
            self.assertTrue(result)
            mock_send.assert_called_once()
            
            # Check that the call was made with correct parameters
            call_args = mock_send.call_args
            self.assertIn("Processing Summary", call_args[0][0])
            self.assertEqual(call_args[0][1], "warning")  # Should be warning since there are failures

if __name__ == '__main__':
    unittest.main()