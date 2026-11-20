from __future__ import annotations

from typing import Literal

DependencyName = Literal["postgresql", "mongodb"]


class DependencyUnavailableError(Exception):
    def __init__(self, dependency: DependencyName):
        if dependency not in ("postgresql", "mongodb"):
            raise ValueError("Unsupported dependency name")
        self.dependency = dependency
        super().__init__(f"{dependency} is unavailable")


class ResourceNotFoundError(Exception):
    pass


class InvalidRequestError(Exception):
    pass


class AuthenticationRequiredError(Exception):
    pass


class PermissionDeniedError(Exception):
    pass


class RateLimitExceededError(Exception):
    pass


class ConflictError(Exception):
    pass
