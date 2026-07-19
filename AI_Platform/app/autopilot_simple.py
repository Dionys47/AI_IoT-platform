# app/autopilot_simple.py
"""
Modul i thjeshtë Autopilot për zbulim automatik të anomalive
"""

import threading
import time
import requests
import logging
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)

class SimpleAutopilot:
    """Version i thjeshtë i Autopilot për monitorim automatik"""
    
    def __init__(self, api_url="http://localhost:8000"):
        self.api_url = api_url
        self.token = None
        self.is_running = False
        self.monitoring_interval = 30
        self.thread = None
        self.notifications = []
        self.threshold_sigma = 2.5
        
    def login(self):
        """Login në API"""
        try:
            response = requests.post(
                f"{self.api_url}/auth/login",
                data={"username": "admin", "password": "admin123"},
                timeout=5
            )
            if response.status_code == 200:
                self.token = response.json()["access_token"]
                logger.info("Autopilot u lidh me API")
                return True
        except Exception as e:
            logger.error(f"Gabim lidhjeje: {e}")
        return False
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
    
    def get_devices(self):
        """Merr listën e pajisjeve"""
        try:
            response = requests.get(f"{self.api_url}/devices", headers=self.get_headers(), timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Gabim gjatë marrjes së pajisjeve: {e}")
        return []
    
    def get_device_data(self, device_id, limit=30):
        """Merr të dhënat e pajisjes"""
        try:
            response = requests.get(
                f"{self.api_url}/devices/{device_id}/data?limit={limit}",
                headers=self.get_headers(),
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                return [d["value"] for d in data]
        except Exception as e:
            logger.error(f"Gabim gjatë marrjes së të dhënave: {e}")
        return []
    
    def detect_anomalies(self, values):
        """Zbulon anomalitë në të dhëna"""
        if len(values) < 5:
            return []
        
        mean_val = np.mean(values)
        std_val = np.std(values)
        
        if std_val == 0:
            return []
        
        z_scores = np.abs((np.array(values) - mean_val) / std_val)
        anomaly_indices = np.where(z_scores > self.threshold_sigma)[0]
        
        return [values[i] for i in anomaly_indices]
    
    def send_notification(self, device_name, anomaly_values):
        """Dërgon njoftim"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        notification = {
            "device": device_name,
            "anomaly_count": len(anomaly_values),
            "anomaly_values": anomaly_values,
            "timestamp": timestamp,
            "severity": "high" if len(anomaly_values) > 3 else "medium" if len(anomaly_values) > 1 else "low"
        }
        
        self.notifications.insert(0, notification)
        
        # Ruaj në skedar
        with open("autopilot_log.txt", "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] PAJISJA: {device_name} | ANOMALI: {len(anomaly_values)} | VLERAT: {anomaly_values}\n")
        
        # Print në console
        print(f"\n🔔 [NJOF TIM] Autopilot - Anomali e Zbuluar!")
        print(f"📱 Pajisja: {device_name}")
        print(f"⚠️ Vlerat anomale: {anomaly_values}°C")
        print(f"🕐 Koha: {timestamp}\n")
        
        return notification
    
    def monitor(self):
        """Funksioni kryesor i monitorimit"""
        logger.info("Autopilot filloi monitorimin...")
        
        while self.is_running:
            try:
                # Rifresko token-in
                if not self.login():
                    time.sleep(10)
                    continue
                
                # Merr pajisjet
                devices = self.get_devices()
                
                if not devices:
                    time.sleep(self.monitoring_interval)
                    continue
                
                for device in devices:
                    if not self.is_running:
                        break
                    
                    device_id = device["id"]
                    device_name = device["name"]
                    
                    # Merr të dhënat
                    values = self.get_device_data(device_id, limit=30)
                    
                    if len(values) < 10:
                        continue
                    
                    # Zbulo anomalitë
                    anomalies = self.detect_anomalies(values)
                    
                    if anomalies:
                        self.send_notification(device_name, anomalies)
                        
                        # Krijo alert në sistem
                        try:
                            alert_data = {
                                "device_id": device_id,
                                "alert_type": "autopilot_anomaly",
                                "title": f"Anomali në {device_name}",
                                "description": f"Janë zbuluar {len(anomalies)} anomali: {anomalies}",
                                "severity": "high" if len(anomalies) > 3 else "medium"
                            }
                            requests.post(
                                f"{self.api_url}/alerts",
                                json=alert_data,
                                headers=self.get_headers(),
                                timeout=5
                            )
                        except:
                            pass
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Gabim në monitorim: {e}")
                time.sleep(10)
    
    def start(self):
        """Nis Autopilot-in në një thread të ri"""
        if self.is_running:
            return False
        
        self.is_running = True
        self.thread = threading.Thread(target=self.monitor, daemon=True)
        self.thread.start()
        logger.info("🚀 Autopilot u aktivizua!")
        return True
    
    def stop(self):
        """Ndalon Autopilot-in"""
        self.is_running = False
        logger.info("🛑 Autopilot u çaktivizua!")
        return True
    
    def get_status(self):
        """Kthen statusin aktual"""
        return {
            "is_running": self.is_running,
            "monitoring_interval": self.monitoring_interval,
            "threshold_sigma": self.threshold_sigma,
            "notifications_count": len(self.notifications),
            "last_notification": self.notifications[0] if self.notifications else None
        }
    
    def get_notifications(self, limit=20):
        """Kthen njoftimet e fundit"""
        return self.notifications[:limit]
    
    def set_threshold(self, sigma):
        """Ndryshon pragun"""
        self.threshold_sigma = max(1.0, min(3.0, sigma))

# Instance globale
autopilot = SimpleAutopilot()
