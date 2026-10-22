from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

def utcnow():
    return datetime.now(timezone.utc)

class PairingChallenge(Base):
    __tablename__ = "pairing_challenges"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    device_id: Mapped[str] = mapped_column(String(128))
    device_type: Mapped[str] = mapped_column(String(32))
    label: Mapped[str] = mapped_column(String(128), default="My device")
    otp_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)

class Device(Base):
    __tablename__ = "devices"
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    device_type: Mapped[str] = mapped_column(String(32))
    label: Mapped[str] = mapped_column(String(128))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)

class UserSession(Base):
    __tablename__ = "user_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)

class TaskRecord(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    device_id: Mapped[str] = mapped_column(String(128), index=True)
    owner_email: Mapped[str] = mapped_column(String(320), index=True)
    task_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="queued")
    request_text: Mapped[str] = mapped_column(Text)
    result_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
