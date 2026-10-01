from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Login(BaseModel):
    username: str = Field(min_length=3, max_length=40, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize(cls, value):
        return value.lower()


class Register(Login):
    role: Literal["player", "scout", "admin"] = "player"


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: str = Field(min_length=1, max_length=100)
    position: Literal["Goalkeeper", "Defender", "Midfielder", "Forward"]
    age: int | None = Field(default=None, ge=5, le=100)
    team: str = Field(default="", max_length=100)
    bio: str = Field(default="", max_length=1000)


class Selection(BaseModel):
    player_id: int = Field(ge=1)


class Calibration(BaseModel):
    # Four video pixel corners, in perimeter order: (0,0), (length,0), (length,width), (0,width).
    points: list[tuple[float, float]] = Field(min_length=4, max_length=4)
    field_length: float = Field(ge=5, le=150)
    field_width: float = Field(ge=5, le=100)


class RunAnalysis(BaseModel):
    calibration: Calibration | None = None
