import socket
import json
import threading
import time
from datetime import datetime
from typing import Dict, Optional, List
import uuid

from .discovery import PeerDiscovery
from .types import Peer, Message
from ..config.settings import Config

class UDPPeerDiscovery(PeerDiscovery):
    def __init__(self, username: str, config: Config):
        self.username = username
        self.config = config
        self.peers: Dict[str, Peer] = {}
        self.messages: List[Message] = []
        self.in_live_view = False
        self.running = True

        # Single UDP socket for both broadcast and direct messages
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Allow broadcasting from any interface
        self.udp_socket.bind(('', self.config.port))  # Use empty string instead of '0.0.0.0'

    def start(self):
        """Start all services"""
        self._start_threads()

    def stop(self):
        """Stop all services"""
        self.running = False
        self.udp_socket.close()

    def _start_threads(self):
        """Start the broadcast and listener threads"""
        self.broadcast_thread = threading.Thread(target=self._broadcast_presence)
        self.broadcast_thread.daemon = True
        self.broadcast_thread.start()

        self.listen_thread = threading.Thread(target=self._listen_for_packets)
        self.listen_thread.daemon = True
        self.listen_thread.start()

    def debug_print(self, message: str):
        """Print debug message if enabled"""
        self.config.load_config()
        if self.config.debug and not self.in_live_view:
            self.config.add_debug_message(message)

    def _broadcast_presence(self):
        """Broadcast presence periodically"""
        while self.running:
            try:
                message = {
                    'type': 'announcement',
                    'username': self.username,
                    'timestamp': datetime.now().isoformat()
                }
                # Use '<broadcast>' instead of '255.255.255.255'
                self.udp_socket.sendto(
                    json.dumps(message).encode(),
                    ('<broadcast>', self.config.port)
                )
                self.debug_print(f"Broadcasting presence: {self.username}")
            except Exception as e:
                self.debug_print(f"Broadcast error: {e}")
                # Add more detailed error info
                self.debug_print(f"Error details: {str(e)}")
            time.sleep(self.config.broadcast_interval)

    def _listen_for_packets(self):
        """Listen for both broadcasts and direct messages"""
        self.debug_print(f"Started listening for packets on port {self.config.port}")
        while self.running:
            try:
                data, addr = self.udp_socket.recvfrom(4096)
                self.debug_print(f"Received raw data from {addr}")
                packet = json.loads(data.decode())
                self.debug_print(f"Decoded packet type: {packet['type']}")
                
                if packet['type'] == 'announcement':
                    self._handle_announcement(packet, addr)
                elif packet['type'] == 'message':
                    self._handle_message(packet)
                
            except Exception as e:
                if self.running:
                    self.debug_print(f"Packet receiving error: {e}")
                    self.debug_print(f"Error details: {str(e)}")

    def _handle_announcement(self, packet: Dict, addr: tuple):
        """Handle peer announcements"""
        if packet['username'] != self.username:
            now = datetime.now()
            self.peers[packet['username']] = Peer(
                username=packet['username'],
                address=addr[0],
                last_seen=now,
                first_seen=now if packet['username'] not in self.peers else 
                          self.peers[packet['username']].first_seen
            )
            self.debug_print(f"Updated peer: {packet['username']} at {addr[0]}")

    def _handle_message(self, packet: Dict):
        """Handle incoming messages"""
        try:
            msg = Message.from_dict(packet['data'])
            if msg.recipient == self.username:
                self.messages.append(msg)
                self.debug_print(f"Received message from {msg.sender}: {msg.title}")
        except Exception as e:
            self.debug_print(f"Message handling error: {e}")

    def send_message(self, recipient: str, title: str, content: str, 
                    conversation_id: Optional[str] = None,
                    reply_to: Optional[str] = None) -> Optional[Message]:
        """Send a message directly to a peer via UDP"""
        peer = self.peers.get(recipient)
        if not peer:
            return None

        try:
            message = Message(
                id=str(uuid.uuid4()),
                sender=self.username,
                recipient=recipient,
                title=title,
                content=content,
                timestamp=datetime.now(),
                conversation_id=conversation_id or str(uuid.uuid4()),
                reply_to=reply_to
            )

            packet = {
                'type': 'message',
                'data': message.to_dict()
            }

            self.udp_socket.sendto(
                json.dumps(packet).encode(),
                (peer.address, self.config.port)
            )
            
            self.messages.append(message)
            self.debug_print(f"Sent message to {recipient} at {peer.address}: {title}")
            return message

        except Exception as e:
            self.debug_print(f"Error sending message: {e}")
            return None

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

    def list_messages(self, peer: Optional[str] = None) -> List[Message]:
        """List all messages or messages with specific peer"""
        if peer:
            return [msg for msg in self.messages 
                   if msg.sender == peer or msg.recipient == peer]
        return self.messages

    def get_conversation(self, conversation_id: str) -> List[Message]:
        """Get all messages in a conversation"""
        return [msg for msg in self.messages 
                if msg.conversation_id == conversation_id]

    def cleanup(self):
        """Clean up resources"""
        self.stop()