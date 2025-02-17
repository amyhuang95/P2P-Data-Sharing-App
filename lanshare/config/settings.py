from pathlib import Path
import json

class Config:
    def __init__(self):
        self.debug = False
        self.debug_messages = []
        self.config_file = Path.home() / '.lanshare.conf'
        self.max_debug_messages = 100
        self.port = 12345  # Single port for all UDP communication
        self.peer_timeout = 2.0  # seconds
        self.broadcast_interval = 0.1  # seconds
        self.load_config()
    
    def load_config(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.debug = config.get('debug', False)
            except Exception as e:
                print(f"Error loading config: {e}")

    def save_config(self):
        try:
            with open(self.config_file, 'w') as f:
                json.dump({'debug': self.debug}, f)
        except Exception as e:
            print(f"Error saving config: {e}")

    def add_debug_message(self, message):
        """Add a debug message to the history"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.debug_messages.append((timestamp, message))
        if len(self.debug_messages) > self.max_debug_messages:
            self.debug_messages.pop(0)
            