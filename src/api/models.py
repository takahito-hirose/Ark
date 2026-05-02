from typing import Optional
from pydantic import BaseModel

class CommandRequest(BaseModel):
    command: str
    workspace_path: Optional[str] = None
    auto_approve_search: bool = False
    architect_provider: Optional[str] = None
    coder_provider: Optional[str] = None
    reviewer_provider: Optional[str] = None
    reflector_provider: Optional[str] = None