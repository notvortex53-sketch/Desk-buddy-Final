from pydantic import BaseModel, EmailStr, Field, HttpUrl
from typing import Literal

DeviceType = Literal["windows", "android", "esp32c3"]
ActionName = Literal["get_status", "open_url"]

class PairStartRequest(BaseModel):
    email: EmailStr
    device_id: str = Field(min_length=3, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    device_type: DeviceType
    label: str = Field(default="My device", min_length=1, max_length=128)

class PairStartResponse(BaseModel):
    challenge_id: str
    expires_in_seconds: int
    message: str

class PairVerifyRequest(BaseModel):
    challenge_id: str = Field(min_length=36, max_length=36)
    otp: str = Field(pattern=r"^\d{6}$")

class PairVerifyResponse(BaseModel):
    device_id: str
    device_token: str
    session_token: str
    session_expires_in_seconds: int
    warning: str = "Save the device credential securely. It is shown only once."

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)

class ChatResponse(BaseModel):
    answer: str
    model: str

class TaskCreateRequest(BaseModel):
    device_id: str = Field(min_length=3, max_length=128)
    action: ActionName
    url: HttpUrl | None = None
    ethical_mode_approved: bool = False

class TaskCreateResponse(BaseModel):
    task_id: str
    status: str

class WindowsCredentialRenewResponse(BaseModel):
    device_id: str
    device_token: str
    websocket_url: str
    connection_command: str
    warning: str = "Save the device credential securely. It is shown only once."

class SessionInfo(BaseModel):
    email: EmailStr
    expires_at: str
