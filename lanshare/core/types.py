from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any

@dataclass
class Peer:
    username: str
    address: str
    last_seen: datetime
    first_seen: datetime

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Peer':
        return cls(
            username=data['username'],
            address=data['address'],
            last_seen=data['last_seen'],
            first_seen=data['first_seen']
        )