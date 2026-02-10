from dataclasses import dataclass
from typing import List, Optional

from app.core.roles import Role


@dataclass
class User:
    id: str
    email: str
    roles: List[Role]
    permissions: List[str]
    display_name: Optional[str] = None
