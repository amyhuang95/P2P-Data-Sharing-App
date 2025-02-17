import socket
import json
import threading
import time
from datetime import datetime
from typing import Dict

from ..config.settings import Config
from .types import Peer
from .discovery import PeerDiscovery

class UDPPeerDiscovery(PeerDiscovery):
    def __init__(self, username: str, config: Config):
        self.username = username
        self.config = config
        self.peers: Dict[str, Peer] = {}
        self.in_live_view = False
        self.running = True

        # Initialize socket
        self.broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.broadcast_socket.bind(('', self.config.broadcast_port))
        
        # Start threads
        self._start_threads()

    def _start_threads(self) -> None:
        """Start the broadcast and listener threads"""
        self.listen_thread = threading.Thread(target=self._listen_for_peers)
        self.listen_thread.daemon = True
        self.listen_thread.start()
        
        self.broadcast_thread = threading.Thread(target=self._broadcast_presence)
        self.broadcast_thread.daemon = True
        self.broadcast_thread.start()

    def debug_print(self, message: str) -> None:
        """Print debug message if debug mode is enabled and not in live view"""
        self.config.load_config()
        if self.config.debug and not self.in_live_view:
            self.config.add_debug_message(message)

    def _broadcast_presence(self) -> None:
        """Continuously broadcast presence to the network"""
        while self.running:
            message = {
                'username': self.username,
                'timestamp': datetime.now().isoformat(),
                'type': 'announcement'
            }
            try:
                self.broadcast_socket.sendto(
                    json.dumps(message).encode(),
                    ('<broadcast>', self.config.broadcast_port)
                )
                self.debug_print(f"Broadcasting presence: {message['username']}")
            except Exception as e:
                self.debug_print(f"Broadcast error: {e}")
            time.sleep(self.config.broadcast_interval)

    def _listen_for_peers(self) -> None:
        """Listen for other peers on the network"""
        while self.running:
            try:
                data, addr = self.broadcast_socket.recvfrom(1024)
                message = json.loads(data.decode())
                self.debug_print(f"Received message from {addr[0]}: {message}")
                
                if message['type'] == 'announcement':
                    if message['username'] != self.username:
                        now = datetime.now()
                        self.peers[message['username']] = Peer(
                            username=message['username'],
                            address=addr[0],
                            last_seen=now,
                            first_seen=now if message['username'] not in self.peers else 
                                      self.peers[message['username']].first_seen
                        )
                        self.debug_print(f"Added/Updated peer: {message['username']} at {addr[0]}")
            except Exception as e:
                self.debug_print(f"Error receiving peer announcement: {e}")

    def list_peers(self) -> Dict[str, Peer]:
        """Return list of active peers"""
        current_time = datetime.now()
        active_peers = {}
        for username, peer in self.peers.items():
            time_diff = (current_time - peer.last_seen).total_seconds()
            if time_diff <= self.config.peer_timeout:
                active_peers[username] = peer
            else:
                self.debug_print(f"Removing {username} - not seen for {time_diff:.1f} seconds")
        
        self.peers = active_peers
        return active_peers

    def cleanup(self) -> None:
        """Clean up resources"""
        self.running = False
        self.broadcast_socket.close()