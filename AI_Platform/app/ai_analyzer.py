# modify_analyzer.py
import requests
import time

BASE_URL = "http://localhost:8000"

print("Modifying AI analyzer to use 2 sigma threshold...")

# Login
r = requests.post(f"{BASE_URL}/auth/login", data={"username": "admin", "password": "admin123"})
token = r.json()["access_token"]

# Get the current ai_analyzer.py
headers = {"Authorization": f"Bearer {token}"}

# Create a modified version
modified_code = '''
import numpy as np
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class IoTDataAnalyzer:
    def __init__(self):
        logger.info("AI Analyzer initialized - Using 2 sigma threshold")
    
    def detect_anomalies(self, data: List[float]) -> Dict[str, Any]:
        if len(data) < 10:
            return {"error": "Need at least 10 data points"}
        
        mean_val = np.mean(data)
        std_val = np.std(data)
        
        if std_val == 0:
            anomaly_indices = []
        else:
            # CHANGED: Using 2 sigma instead of 3 sigma
            z_scores = np.abs((np.array(data) - mean_val) / std_val)
            anomaly_indices = np.where(z_scores > 2)[0]  # Changed from 3 to 2
        
        return {
            "total_samples": len(data),
            "anomalies_detected": len(anomaly_indices),
            "anomaly_percentage": (len(anomaly_indices) / len(data)) * 100,
            "mean": float(mean_val),
            "std": float(std_val),
            "anomaly_indices": anomaly_indices.tolist(),
            "is_normal": len(anomaly_indices) / len(data) < 0.1
        }
# Shto këtë funksion në app/ai_analyzer.py

def predict_future_trend(self, historical_data: List[float], hours_ahead: int = 24) -> Dict[str, Any]:
    """
    Parashikon trendin e të dhënave për orët e ardhshme
    
    Args:
        historical_data: Të dhënat historike (minimum 50 pikë)
        hours_ahead: Sa orë përpara për të parashikuar (default: 24)
    
    Returns:
        Dictionary me parashikimet dhe metrikat
    """
    import numpy as np
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import PolynomialFeatures
    
    if len(historical_data) < 50:
        return {"error": "Nevojiten të paktën 50 pikë të dhënash për parashikim"}
    
    try:
        # Përgatit të dhënat
        X = np.arange(len(historical_data)).reshape(-1, 1)
        y = np.array(historical_data)
        
        # Modeli i regresionit polinomial (shkalla 2 për trend jo-linear)
        poly = PolynomialFeatures(degree=2)
        X_poly = poly.fit_transform(X)
        
        model = LinearRegression()
        model.fit(X_poly, y)
        
        # Parashiko të ardhmen
        future_steps = hours_ahead * 6  # Supozojmë 6 pikë në orë (çdo 10 minuta)
        future_X = np.arange(len(historical_data), len(historical_data) + future_steps).reshape(-1, 1)
        future_X_poly = poly.transform(future_X)
        predictions = model.predict(future_X_poly)
        
        # Llogarit intervalet e besimit
        residuals = y - model.predict(X_poly)
        std_residual = np.std(residuals)
        confidence_interval = 1.96 * std_residual  # 95% confidence interval
        
        # Gjej trendin
        slope = (predictions[-1] - predictions[0]) / len(predictions)
        
        # Identifiko pikat e mundshme të anomalive në parashikim
        mean_val = np.mean(predictions)
        std_val = np.std(predictions)
        anomaly_threshold_high = mean_val + (2 * std_val)
        anomaly_threshold_low = mean_val - (2 * std_val)
        
        alert_points = []
        for i, val in enumerate(predictions):
            if val > anomaly_threshold_high or val < anomaly_threshold_low:
                alert_points.append({
                    "hour": i / 6,  # konverto në orë
                    "value": float(val),
                    "severity": "high" if val > anomaly_threshold_high else "low"
                })
        
        return {
            "success": True,
            "historical_points": len(historical_data),
            "prediction_hours": hours_ahead,
            "predictions": [float(p) for p in predictions],
            "prediction_timestamps": [(datetime.now() + timedelta(hours=i/6)).isoformat() for i in range(len(predictions))],
            "confidence_interval": float(confidence_interval),
            "trend": "increasing" if slope > 0 else "decreasing",
            "trend_strength": abs(float(slope)),
            "expected_range": {
                "min": float(np.min(predictions)),
                "max": float(np.max(predictions)),
                "average": float(np.mean(predictions))
            },
            "alert_points": alert_points[:10],  # Vetëm 10 të parat
            "recommendations": self._generate_prediction_recommendations(predictions, slope)
        }
        
    except Exception as e:
        logger.error(f"Error in trend prediction: {e}")
        return {"error": str(e), "success": False}

def _generate_prediction_recommendations(self, predictions, slope):
    """Gjeneron rekomandime bazuar në parashikim"""
    recommendations = []
    
    max_pred = np.max(predictions)
    min_pred = np.min(predictions)
    range_val = max_pred - min_pred
    
    if slope > 0.1:
        recommendations.append("📈 Temperatura në rritje - Përgatituni për ngrohje")
    elif slope < -0.1:
        recommendations.append("📉 Temperatura në rënie - Përgatituni për ftohje")
    
    if range_val > 10:
        recommendations.append("⚠️ Luhatje të mëdha të parashikuara - Monitoroni nga afër")
    
    if max_pred > 35:
        recommendations.append("🔥 Vlera ekstreme të parashikuara - Kontrolloni sistemin e ftohjes")
    
    if min_pred < 10:
        recommendations.append("❄️ Vlera të ulëta të parashikuara - Kontrolloni sistemin e ngrohjes")
    
    if not recommendations:
        recommendations.append("✅ Trend stabil i parashikuar - Vazhdoni monitorimin normal")
    
    return recommendations
'''

# Save and copy to container (manual steps needed)
print("\nManual steps required:")
print("1. Copy the modified code above")
print("2. Run: docker cp modified_analyzer.py iot_ai_api:/app/ai_analyzer.py")
print("3. Run: docker-compose restart api")