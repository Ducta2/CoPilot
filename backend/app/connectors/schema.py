from datetime import datetime
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator


class ConnectorHistoryResponse(BaseModel):
    id: Optional[int] = None
    connector_id: int
    change_timestamp: datetime
    change_description: str
    model_config = ConfigDict(from_attributes=True)


class ConnectorResponse(BaseModel):
    id: Optional[int] = None
    connector_name: str
    connector_type: str
    connector_url: str
    connector_last_updated: datetime
    connector_username: Optional[str] = None
    connector_password: Optional[str] = None
    connector_api_key: Optional[str] = None
    connector_description: Optional[str] = None
    connector_supports: Optional[str] = None
    connector_configured: bool
    connector_verified: bool
    connector_enabled: bool
    connector_accepts_host_only: bool
    connector_accepts_api_key: bool
    connector_accepts_username_password: bool
    connector_accepts_file: bool
    connector_accepts_extra_data: bool
    connector_extra_data: Optional[str] = None
    history_logs: Optional[List[ConnectorHistoryResponse]] = None
    model_config = ConfigDict(from_attributes=True)


class ConnectorPublicResponse(ConnectorResponse):
    """A connector as the API returns it: stored secrets never leave the backend.

    ``ConnectorResponse`` stays the internal shape (verification and provisioning code
    reads the password / API key from it). Routes answer with this model instead, so
    the plaintext ``connector_password`` and ``connector_api_key`` are dropped from the
    JSON and replaced by ``*_set`` flags the UI can show ("a password is stored").
    """

    connector_password: Optional[str] = Field(default=None, exclude=True)
    connector_api_key: Optional[str] = Field(default=None, exclude=True)
    connector_password_set: bool = False
    connector_api_key_set: bool = False

    @model_validator(mode="after")
    def _flag_stored_secrets(self) -> "ConnectorPublicResponse":
        self.connector_password_set = bool(self.connector_password)
        self.connector_api_key_set = bool(self.connector_api_key)
        return self


class ConnectorsListResponse(BaseModel):
    connectors: List[ConnectorPublicResponse]
    success: bool
    message: str


class ConnectorListResponse(BaseModel):
    connector: ConnectorPublicResponse
    success: bool
    message: str


class VerifyConnectorResponse(BaseModel):
    connectionSuccessful: bool
    message: str


class UpdateConnector(BaseModel):
    """Connector update. A secret left out (or sent empty) keeps the stored value:
    the API no longer returns secrets, so a client cannot echo them back."""

    connector_url: str
    connector_username: Optional[str] = None
    connector_password: Optional[str] = None
    connector_api_key: Optional[str] = None
    connector_extra_data: Optional[str] = None
