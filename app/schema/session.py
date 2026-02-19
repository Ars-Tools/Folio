from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

class Category(str, Enum):
    unknown = "unknown"
    system = "system"
    agent = "agent"
    user = "user"

class Sender(BaseModel):
    id: str = Field(description="The unique identifier for the sender")
    name: str = Field(description="The name of the sender")
    category: Category = Field(description="The category of the sender")

class Session(BaseModel):
    id: str = Field(description="The unique identifier for the session")
    sender: Sender = Field(description="The sender associated with this session")
    parent: str | None = Field(default=None, description="The parent session ID, if this is a sub-session")
    docker: str | None = Field(default=None, description="The Docker container associated with this session, if any")
    # sandbox: str | None = Field(default=None, description="The sandbox environment associated with this session, if any")
    # sender: Sender = Field(description="The sender associated with this session")
    # timestamp: datetime = Field(description="The timestamp when the session was created")
    def __init__(self, **data):
        super().__init__(**data)
        # if not self.timestamp:
            # self.timestamp = datetime.utcnow()