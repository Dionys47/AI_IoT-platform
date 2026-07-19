# app/notifications.py
import requests
import asyncio
import logging

logger = logging.getLogger(__name__)

# Konfigurimi i Telegram Bot
# Krijo një bot te @BotFather në Telegram dhe merr token-in
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN"  # Zëvendëso me token-in tënd
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"      # Zëvendëso me chat ID-në tënde

class NotificationManager:
    def __init__(self):
        self.webhook_url = None
        self.alerts_queue = []
    
    def send_telegram(self, message):
        """Dërgon njoftim në Telegram"""
        if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN":
            logger.warning("Telegram bot not configured")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(url, json=data, timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Telegram error: {e}")
            return False
    
    def send_email(self, to_email, subject, body):
        """Dërgon njoftim me email (SMTP)"""
        # Implemento sipas nevojës
        pass
    
    def send_webhook(self, url, data):
        """Dërgon njoftim në webhook"""
        try:
            response = requests.post(url, json=data, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def anomaly_alert(self, device_name, value, threshold):
        """Krijon njoftim për anomali"""
        message = f"""
🚨 <b>ANOMALY DETECTED!</b> 🚨

📱 <b>Device:</b> {device_name}
🌡️ <b>Value:</b> {value}
⚠️ <b>Threshold:</b> {threshold}
🕐 <b>Time:</b> {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔍 Please check the device immediately!
        """
        return self.send_telegram(message)
    
    def prediction_alert(self, device_name, predicted_value, time_frame):
        """Njoftim për parashikim"""
        message = f"""
📊 <b>PREDICTION ALERT</b> 📊

📱 <b>Device:</b> {device_name}
🔮 <b>Predicted:</b> {predicted_value}
⏰ <b>Time frame:</b> Next {time_frame} hours

💡 Consider preventive maintenance.
        """
        return self.send_telegram(message)

notifier = NotificationManager()
