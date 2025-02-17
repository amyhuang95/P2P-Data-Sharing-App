from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional

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
        
@dataclass
class Message:
    id: str
    sender: str
    recipient: str
    title: str
    content: str
    timestamp: datetime
    conversation_id: Optional[str] = None
    reply_to: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        return cls(
            id=data['id'],
            sender=data['sender'],
            recipient=data['recipient'],
            title=data['title'],
            content=data['content'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            conversation_id=data.get('conversation_id'),
            reply_to=data.get('reply_to')
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'sender': self.sender,
            'recipient': self.recipient,
            'title': self.title,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'conversation_id': self.conversation_id,
            'reply_to': self.reply_to
        }