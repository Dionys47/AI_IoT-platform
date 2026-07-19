from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

class DeviceType(str, Enum):
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    GATEWAY = "gateway"

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserInDB(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class TokenData(BaseModel):
    username: Optional[str] = None

class IoTDeviceBase(BaseModel):
    name: str
    device_type: DeviceType
    location: Optional[str] = None

class IoTDeviceCreate(IoTDeviceBase):
    pass

class IoTDeviceInDB(IoTDeviceBase):
    id: str
    status: str
    owner_id: int
    created_at: datetime
    class Config:
        from_attributes = True

class SensorDataCreate(BaseModel):
    device_id: str
    sensor_type: str
    value: float
    unit: Optional[str] = None
    timestamp: Optional[datetime] = None

class SensorDataInDB(BaseModel):
    id: int
    device_id: str
    sensor_type: str
    value: float
    unit: Optional[str] = None
    timestamp: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True

class AnalysisRequest(BaseModel):
    device_id: str
    sensor_type: str
    start_date: datetime
    end_date: datetime
    analysis_type: str = "anomaly_detection"

class AlertBase(BaseModel):
    device_id: str
    alert_type: str
    title: str
    description: Optional[str] = None
    severity: str = "medium"

class AlertCreate(AlertBase):
    pass

class AlertInDB(AlertBase):
    id: int
    is_resolved: bool
    created_at: datetime
    class Config:
        from_attributes = True
