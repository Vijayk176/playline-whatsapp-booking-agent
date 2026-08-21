import enum
from datetime import datetime, date, time
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date, Time,
    ForeignKey, Text, Enum, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from app.database import Base


class BookingStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"
    no_show = "no_show"


class PaymentStatus(str, enum.Enum):
    unpaid = "unpaid"
    paid = "paid"
    refunded = "refunded"


class MessageSender(str, enum.Enum):
    customer = "customer"
    ai = "ai"
    admin = "admin"
    system = "system"


class SupportStatus(str, enum.Enum):
    open = "open"
    assigned = "assigned"
    resolved = "resolved"


class ConversationState(str, enum.Enum):
    idle = "idle"
    collecting_name = "collecting_name"
    collecting_game = "collecting_game"
    collecting_date = "collecting_date"
    collecting_time = "collecting_time"
    collecting_duration = "collecting_duration"
    awaiting_confirmation = "awaiting_confirmation"
    booking_confirmed = "booking_confirmed"
    cancelling = "cancelling"
    rescheduling = "rescheduling"
    human_handoff = "human_handoff"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=True)
    phone = Column(String(32), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    bookings = relationship("Booking", back_populates="customer")
    conversations = relationship("Conversation", back_populates="customer")


class GamingOption(Base):
    __tablename__ = "gaming_options"
    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False, index=True)
    description = Column(Text, default="")
    price_per_hour = Column(Float, nullable=False)
    capacity = Column(Integer, default=1)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    bookings = relationship("Booking", back_populates="gaming_option")


class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True)
    booking_ref = Column(String(32), unique=True, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    gaming_option_id = Column(Integer, ForeignKey("gaming_options.id"), nullable=False)

    customer_name = Column(String(128), nullable=False)
    phone = Column(String(32), nullable=False, index=True)

    booking_date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    duration_hours = Column(Float, nullable=False)
    end_time = Column(Time, nullable=False)

    price = Column(Float, nullable=False)
    status = Column(Enum(BookingStatus), default=BookingStatus.pending, index=True)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.unpaid)
    notes = Column(Text, default="")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="bookings")
    gaming_option = relationship("GamingOption", back_populates="bookings")

    __table_args__ = (
        Index("ix_booking_date_game_status", "booking_date", "gaming_option_id", "status"),
    )


class BusinessSetting(Base):
    __tablename__ = "business_settings"
    id = Column(Integer, primary_key=True)
    business_name = Column(String(128), default="Your Gaming Zone Name (SAMPLE - set in Settings)")
    address = Column(String(255), default="SAMPLE ADDRESS - replace with your real address")
    phone = Column(String(32), default="0300-0000000 (SAMPLE)")
    whatsapp_number = Column(String(32), default="0300-0000000 (SAMPLE)")
    opening_time = Column(Time, default=time(12, 0))
    closing_time = Column(Time, default=time(23, 59))
    weekly_closed_day = Column(String(16), default="None")
    google_maps_link = Column(String(255), default="https://maps.google.com/?q=YOUR+BUSINESS (SAMPLE)")
    instagram_link = Column(String(255), default="https://instagram.com/SAMPLE")
    facebook_link = Column(String(255), default="https://facebook.com/SAMPLE")
    general_description = Column(Text, default="SAMPLE DESCRIPTION - replace with a description of your gaming zone.")
    ai_greeting = Column(Text, default="Assalam o Alaikum! Welcome. How can I help you today?")
    ai_instructions = Column(Text, default="Be friendly, concise, and helpful. Never invent prices or availability.")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SupportRequest(Base):
    __tablename__ = "support_requests"
    id = Column(Integer, primary_key=True)
    customer_phone = Column(String(32), nullable=False, index=True)
    customer_name = Column(String(128), default="")
    message = Column(Text, default="")
    status = Column(Enum(SupportStatus), default=SupportStatus.open, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    channel = Column(String(32), default="whatsapp")
    status = Column(String(32), default="active")
    state = Column(Enum(ConversationState), default=ConversationState.idle)
    state_data = Column(Text, default="{}")  # JSON blob of partial booking info
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    sender = Column(Enum(MessageSender), nullable=False)
    message = Column(Text, nullable=False)
    wa_message_id = Column(String(128), nullable=True, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id = Column(Integer, primary_key=True)
    action = Column(String(64), nullable=False)
    actor = Column(String(64), default="system")
    log_metadata = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)
