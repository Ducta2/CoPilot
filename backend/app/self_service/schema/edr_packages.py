from datetime import datetime
from enum import Enum
from typing import List
from typing import Literal
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator

GROUP_PATTERN = r"^[A-Za-z0-9_-]{1,40}$"


class EdrPlatform(str, Enum):
    windows = "windows"
    linux = "linux"
    macos = "macos"


class EdrPackageCreate(BaseModel):
    customer_code: str = Field(..., min_length=1, max_length=50)
    platform: EdrPlatform
    arch: Literal["x64", "arm64", "x86"]
    # Absent or empty means the customer code (the Console's default).
    group: Optional[str] = Field(default=None, pattern=GROUP_PATTERN, description="Asset group; defaults to the customer code")
    max_installs: int = Field(..., ge=1, le=500)
    valid_days: Literal[1, 7, 30]

    @field_validator("group", mode="before")
    @classmethod
    def _empty_group_is_default(cls, value):
        return None if value == "" else value


class EdrPackageOut(BaseModel):
    """The Console's ``EdrPackage``, plus ``enforced``: false while the limits are records only (Level 1)."""

    id: str
    customer_code: str
    platform: EdrPlatform
    arch: str
    group: str
    created_by: str
    created_at: datetime
    expires_at: datetime
    max_installs: int
    enrolled: int
    status: Literal["active", "expired", "revoked"]
    enforced: bool = False


class EdrPackageListResponse(BaseModel):
    packages: List[EdrPackageOut]
    success: bool
    message: str


class EdrPackageResponse(BaseModel):
    package: EdrPackageOut
    success: bool
    message: str
