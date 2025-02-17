from abc import ABC, abstractmethod
from typing import Dict
from .types import Peer

class PeerDiscovery(ABC):
    """Base interface for peer discovery implementations"""
    
    @abstractmethod
    def _start_threads(self) -> None:
        """Start the necessary threads for peer discovery"""
        pass

    @abstractmethod
    def debug_print(self, message: str) -> None:
        """Print debug messages"""
        pass

    @abstractmethod
    def list_peers(self) -> Dict[str, Peer]:
        """List all currently active peers"""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources"""
        pass