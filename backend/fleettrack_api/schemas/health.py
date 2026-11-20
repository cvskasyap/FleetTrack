from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class LivenessResponse(BaseModel):
    status: Literal["alive"] = "alive"


class DependencyHealth(BaseModel):
    status: Literal["ok", "unavailable"]


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    postgres: DependencyHealth
    mongodb: DependencyHealth
