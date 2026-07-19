# app/autopilot.py
"""
Moduli Autopilot për zbulim automatik të anomalive dhe njoftime
"""

import asyncio
import logging
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)

class AutopilotMonitor:
    """Monitoron automatikisht pajisjet dhe dërgon njoftime për anomali"""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.token = None
        self.is_running = False
        self.monitoring_interval = 30  # sekonda
        self.notification_history = []
        self.threshold_sigma = 2.5  # Pragu i zbulimit
        
    def login(self) -> bool:
        """Login në API për të marrë token"""
        try:
            response = requests.post(
                f"{self.api_url}/auth/login",
                data={"username": "admin", "password": "admin123"}
            )
            if response.status_code == 200:
                self.token = response.json()["access_token"]
                logger.info("✅ Autopilot u lidh me API")
                return True
            else:
                logger.error("❌ Autopilot nuk mund të lidhej me API")
                return False
        except Exception as e:
            logger.error(f"❌ Gabim lidhjeje: {e}")
            return False
    
    def get_headers(self):
        """Kthen headers për API"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def get_all_devices(self) -> List[Dict]:
        """Merr të gjitha pajisjet"""
        try:
            response = requests.get(
                f"{self.api_url}/devices",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"Gabim gjatë marrjes së pajisjeve: {e}")
            return []
    
    def analyze_device_data(self, device_id: str, values: List[float]) -> Dict:
        """Analizon të dhënat e një pajisjeje"""
        if len(values) < 10:
            return {"has_anomaly": False, "reason": "Të dhëna të pamjaftueshme"}
        
        mean_val = np.mean(values)
        std_val = np.std(values)
        
        if std_val == 0:
            return {"has_anomaly": False, "reason": "Të dhëna konstante"}
        
        # Zbulimi i anomalive me pragun e vendosur
        z_scores = np.abs((np.array(values) - mean_val) / std_val)
        anomaly_indices = np.where(z_scores > self.threshold_sigma)[0]
        anomaly_values = [values[i] for i in anomaly_indices]
        
        return {
            "has_anomaly": len(anomaly_indices) > 0,
            "anomaly_count": len(anomaly_indices),
            "anomaly_values": anomaly_values,
            "mean": float(mean_val),
            "std": float(std_val),
            "threshold": self.threshold_sigma,
            "normal_range": {
                "min": float(mean_val - self.threshold_sigma * std_val),
                "max": float(mean_val + self.threshold_sigma * std_val)
            }
        }
    
    def get_device_data(self, device_id: str, limit: int = 100) -> List[float]:
        """Merr të dhënat e fundit të një pajisjeje"""
        try:
            response = requests.get(
                f"{self.api_url}/devices/{device_id}/data?limit={limit}",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                data = response.json()
                return [d["value"] for d in data]
            return []
        except Exception as e:
            logger.error(f"Gabim gjatë marrjes së të dhënave: {e}")
            return []
    
    def send_notification(self, device_name: str, anomaly_count: int, anomaly_values: List[float]):
        """Dërgon njoftim për anomali të zbuluara"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Njoftimi në console
        print("\n" + "="*60)
        print(f"🔔 [NJOF TIM] Autopilot - Anomali e Zbuluar!")
        print("="*60)
        print(f"📱 Pajisja: {device_name}")
        print(f"📊 Anomalitë e zbuluara: {anomaly_count}")
        print(f"⚠️ Vlerat anomale: {', '.join([str(v) for v in anomaly_values])}°C")
        print(f"🕐 Koha: {timestamp}")
        print("="*60 + "\n")
        
        # Ruaj në histori
        self.notification_history.append({
            "device": device_name,
            "anomaly_count": anomaly_count,
            "anomaly_values": anomaly_values,
            "timestamp": timestamp,
            "severity": "high" if anomaly_count > 5 else "medium" if anomaly_count > 2 else "low"
        })
        
        # Mund të shtohet edhe njoftim me email, SMS, WebHook, etj.
        self._save_notification_to_file(device_name, anomaly_count, anomaly_values, timestamp)
    
    def _save_notification_to_file(self, device_name: str, anomaly_count: int, anomaly_values: List[float], timestamp: str):
        """Ruaj njoftimin në skedar log"""
        import os
        log_file = "autopilot_log.txt"
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] PAJISJA: {device_name} | ANOMALI: {anomaly_count} | VLERAT: {anomaly_values}\n")
    
    async def monitor_devices(self):
        """Monitoron të gjitha pajisjet në mënyrë të vazhdueshme"""
        logger.info("🤖 Autopilot është aktivizuar - Duke monitoruar pajisjet...")
        
        while self.is_running:
            try:
                # Rifresko token-in çdo 30 minuta
                if datetime.now().minute % 30 == 0:
                    self.login()
                
                # Merr të gjitha pajisjet
                devices = self.get_all_devices()
                
                if not devices:
                    logger.warning("Nuk u gjetën pajisje për monitorim")
                    await asyncio.sleep(self.monitoring_interval)
                    continue
                
                # Analizo çdo pajisje
                for device in devices:
                    device_id = device["id"]
                    device_name = device["name"]
                    
                    # Merr të dhënat e fundit
                    values = self.get_device_data(device_id, limit=50)
                    
                    if len(values) < 10:
                        continue
                    
                    # Analizo për anomali
                    analysis = self.analyze_device_data(device_id, values)
                    
                    if analysis["has_anomaly"]:
                        logger.warning(f"⚠️ Anomali në {device_name}: {analysis['anomaly_count']} anomali")
                        self.send_notification(
                            device_name,
                            analysis["anomaly_count"],
                            analysis["anomaly_values"]
                        )
                        
                        # Krijo alert në sistem
                        self.create_alert(device_id, device_name, analysis)
                
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Gabim në monitorim: {e}")
                await asyncio.sleep(10)
    
    def create_alert(self, device_id: str, device_name: str, analysis: Dict):
        """Krijon një alert në sistem për anomali"""
        try:
            alert_data = {
                "device_id": device_id,
                "alert_type": "anomaly_detection_autopilot",
                "title": f"Anomali e zbuluar nga Autopilot në {device_name}",
                "description": f"Janë zbuluar {analysis['anomaly_count']} anomali. Vlerat: {analysis['anomaly_values']}",
                "severity": "high" if analysis["anomaly_count"] > 5 else "medium" if analysis["anomaly_count"] > 2 else "low"
            }
            
            response = requests.post(
                f"{self.api_url}/alerts",
                json=alert_data,
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Alert u krijua për {device_name}")
            else:
                logger.warning(f"⚠️ Nuk u krijua alert për {device_name}")
                
        except Exception as e:
            logger.error(f"Gabim gjatë krijimit të alertit: {e}")
    
    def get_status(self) -> Dict:
        """Kthen statusin aktual të Autopilot"""
        return {
            "is_running": self.is_running,
            "monitoring_interval": self.monitoring_interval,
            "threshold_sigma": self.threshold_sigma,
            "notifications_sent": len(self.notification_history),
            "last_notification": self.notification_history[-1] if self.notification_history else None
        }
    
    def set_threshold(self, sigma: float):
        """Ndryshon pragun e zbulimit"""
        self.threshold_sigma = max(1.0, min(3.0, sigma))
        logger.info(f"Pragu i zbulimit u ndryshua në {self.threshold_sigma}σ")
    
    def start(self):
        """Nis monitorimin automatik"""
        if not self.login():
            logger.error("Nuk mund të niset Autopilot - dështoi login")
            return
        
        self.is_running = True
        logger.info("🚀 Autopilot u aktivizua!")
        
        # Krijo event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.monitor_devices())
    
    def stop(self):
        """Ndalon monitorimin automatik"""
        self.is_running = False
        logger.info("🛑 Autopilot u çaktivizua!")

# Instance globale
autopilot = AutopilotMonitor()

def start_autopilot():
    """Funksion për të nisur Autopilot në background"""
    import threading
    thread = threading.Thread(target=autopilot.start, daemon=True)
    thread.start()
    return thread

def stop_autopilot():
    """Ndalon Autopilot"""
    autopilot.stop()
