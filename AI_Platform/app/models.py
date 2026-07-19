from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255))
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class IoTDevice(Base):
    __tablename__ = "iot_devices"
    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(100))
    device_type = Column(String(50))
    manufacturer = Column(String(100))
    model = Column(String(100))
    location = Column(String(255))
    status = Column(String(20), default="offline")
    last_seen = Column(DateTime)
    battery_level = Column(Integer)
    signal_strength = Column(Integer)
    protocol = Column(String(20), default="mqtt")
    configuration = Column(JSON, default=dict)
    owner_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SensorData(Base):
    __tablename__ = "sensor_data"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(50))
    sensor_type = Column(String(50))
    value = Column(Float)
    unit = Column(String(20))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    raw_value = Column(String(100))
    accuracy = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(50))
    alert_type = Column(String(50))
    severity = Column(String(20), default="medium")
    title = Column(String(200))
    description = Column(String(500))
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)
    ai_confidence = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
