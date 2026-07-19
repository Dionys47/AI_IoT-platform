from sqlalchemy.orm import Session
from app.models import User, IoTDevice, SensorData, Alert
from app import schemas
import uuid
from datetime import datetime
from typing import List, Optional

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate, hashed_password: str):
    db_user = User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        is_active=True,
        is_admin=False
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def create_device(db: Session, device: schemas.IoTDeviceCreate, user_id: int):
    db_device = IoTDevice(
        id=str(uuid.uuid4()),
        name=device.name,
        device_type=device.device_type.value,
        location=device.location,
        owner_id=user_id,
        status="offline"
    )
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device

def get_user_devices(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(IoTDevice).filter(IoTDevice.owner_id == user_id).offset(skip).limit(limit).all()

def create_sensor_data(db: Session, sensor_data: schemas.SensorDataCreate):
    # Krijo të dhënat me timestamp
    now = datetime.utcnow()
    db_data = SensorData(
        device_id=sensor_data.device_id,
        sensor_type=sensor_data.sensor_type,
        value=sensor_data.value,
        unit=sensor_data.unit,
        timestamp=sensor_data.timestamp or now,
        created_at=now
    )
    db.add(db_data)
    db.commit()
    db.refresh(db_data)
    return db_data

def get_sensor_data(db: Session, device_id: str, limit: int = 1000):
    return db.query(SensorData).filter(SensorData.device_id == device_id).order_by(SensorData.timestamp.desc()).limit(limit).all()

def create_alert(db: Session, alert: schemas.AlertCreate):
    db_alert = Alert(
        device_id=alert.device_id,
        alert_type=alert.alert_type,
        title=alert.title,
        description=alert.description,
        severity=alert.severity
    )
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert

def get_alerts(db: Session, user_id: int, resolved: bool = False):
    device_ids = [d.id for d in get_user_devices(db, user_id)]
    return db.query(Alert).filter(Alert.device_id.in_(device_ids)).filter(Alert.is_resolved == resolved).order_by(Alert.created_at.desc()).all()
# Add this function to app/crud.py

def get_device(db: Session, device_id: str):
    """Get device by ID"""
    from models import IoTDevice
    return db.query(IoTDevice).filter(IoTDevice.id == device_id).first()
