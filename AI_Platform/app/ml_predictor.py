# app/ml_predictor.py
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import os
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class MLPredictor:
    """Model Machine Learning për parashikimin e të dhënave IoT"""
    
    def __init__(self, model_path="./models"):
        self.model = None
        self.scaler = StandardScaler()
        self.model_path = model_path
        self.is_trained = False
        
        # Krijo direktorinë për modelet nëse nuk ekziston
        os.makedirs(model_path, exist_ok=True)
    
    def prepare_features(self, data, lookback=10):
        """
        Përgatit tiparet për modelin ML
        Args:
            data: Lista e vlerave historike
            lookback: Numri i vlerave të mëparshme për të parashikuar tashmën
        Returns:
            X (features), y (target)
        """
        if len(data) < lookback + 1:
            return None, None
        
        X, y = [], []
        for i in range(lookback, len(data)):
            X.append(data[i-lookback:i])
            y.append(data[i])
        
        return np.array(X), np.array(y)
    
    def train(self, historical_data, lookback=10, test_size=0.2):
        """
        Trajnon modelin Random Forest
        Args:
            historical_data: Lista e të dhënave historike
            lookback: Numri i vlerave për lookback
            test_size: Përqindja e të dhënave për testim
        Returns:
            Metrikat e performancës
        """
        if len(historical_data) < 50:
            return {"error": "Need at least 50 data points for training"}
        
        # Përgatit tiparet
        X, y = self.prepare_features(historical_data, lookback)
        if X is None:
            return {"error": "Not enough data for feature preparation"}
        
        # Ndarja në train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, shuffle=False
        )
        
        # Normalizimi i të dhënave
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Trajno Random Forest model
        self.model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        self.model.fit(X_train_scaled, y_train)
        
        # Parashiko dhe llogarit metrikat
        y_pred = self.model.predict(X_test_scaled)
        
        mae = mean_absolute_error(y_test, y_pred)
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        r2 = r2_score(y_test, y_pred)
        
        self.is_trained = True
        
        # Ruaj modelin
        joblib.dump(self.model, f"{self.model_path}/rf_model.joblib")
        joblib.dump(self.scaler, f"{self.model_path}/scaler.joblib")
        
        return {
            "success": True,
            "lookback": lookback,
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "metrics": {
                "mae": float(mae),
                "mse": float(mse),
                "rmse": float(rmse),
                "r2": float(r2)
            }
        }
    
    def predict(self, recent_data, lookback=10, steps_ahead=24):
        """
        Parashikon vlerat e ardhshme duke përdorur modelin e trajnuar
        Args:
            recent_data: Të dhënat e fundit historike
            lookback: Numri i vlerave për lookback
            steps_ahead: Sa hapa përpara për të parashikuar
        Returns:
            Lista e parashikimeve
        """
        if not self.is_trained and not self.load_model():
            return None
        
        if len(recent_data) < lookback:
            return None
        
        predictions = []
        current_window = recent_data[-lookback:].copy()
        
        for _ in range(steps_ahead):
            # Normalizo dhe parashiko
            current_scaled = self.scaler.transform([current_window])
            next_val = self.model.predict(current_scaled)[0]
            predictions.append(float(next_val))
            
            # Përditëso dritaren
            current_window = current_window[1:] + [next_val]
        
        return predictions
    
    def load_model(self):
        """Ngarkon modelin e ruajtur"""
        try:
            model_file = f"{self.model_path}/rf_model.joblib"
            scaler_file = f"{self.model_path}/scaler.joblib"
            
            if os.path.exists(model_file) and os.path.exists(scaler_file):
                self.model = joblib.load(model_file)
                self.scaler = joblib.load(scaler_file)
                self.is_trained = True
                return True
        except Exception as e:
            logger.error(f"Error loading model: {e}")
        return False
    
    def get_model_info(self):
        """Kthen informacion rreth modelit"""
        if not self.is_trained:
            return {"status": "not_trained"}
        
        return {
            "status": "trained",
            "type": "RandomForestRegressor",
            "n_estimators": self.model.n_estimators if self.model else 0,
            "max_depth": self.model.max_depth if self.model else 0
        }

# Instance globale
ml_predictor = MLPredictor()
