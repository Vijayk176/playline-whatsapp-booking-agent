from datetime import date, time, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class GamingOptionIn(BaseModel):
    name: str
    description: str = ""
    price_per_hour: float
    capacity: int = 1
    active: bool = True


class GamingOptionOut(GamingOptionIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class BookingIn(BaseModel):
    customer_name: str
    phone: str
    gaming_option_id: int
    booking_date: date
    start_time: time
    duration_hours: float
    notes: str = ""


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    booking_ref: str
    customer_name: str
    phone: str
    gaming_option_id: int
    booking_date: date
    start_time: time
    end_time: time
    duration_hours: float
    price: float
    status: str
    payment_status: str
    notes: str
    created_at: datetime


class BookingStatusUpdate(BaseModel):
    status: str


class PaymentStatusUpdate(BaseModel):
    payment_status: str


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: Optional[str]
    phone: str
    created_at: datetime


class SupportRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    customer_phone: str
    customer_name: str
    message: str
    status: str
    created_at: datetime


class SupportStatusUpdate(BaseModel):
    status: str


class BusinessSettingIn(BaseModel):
    business_name: str
    address: str
    phone: str
    whatsapp_number: str
    owner_notification_phone: str = ""
    opening_time: time
    closing_time: time
    weekly_closed_day: str = "None"
    google_maps_link: str = ""
    instagram_link: str = ""
    facebook_link: str = ""
    general_description: str = ""
    ai_greeting: str = ""
    ai_instructions: str = ""


class AdminLogin(BaseModel):
    username: str
    password: str
