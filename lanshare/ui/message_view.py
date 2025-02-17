from prompt_toolkit.application import Application
from prompt_toolkit.layout.containers import Window, HSplit
from prompt_toolkit.layout.controls import FormattedTextControl, BufferControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.styles import Style
from prompt_toolkit.shortcuts import clear
from datetime import datetime
from typing import List, Optional
import uuid

from ..core.types import Message

class MessageView:
    def __init__(self, discovery, recipient=None):
        self.discovery = discovery
        self.recipient = recipient
        self.running = True
        self.messages: List[Message] = []
        self.message_buffer = Buffer()
        
        # Setup components
        self._setup_keybindings()
        self._setup_styles()

    def _setup_keybindings(self):
        self.kb = KeyBindings()

        @self.kb.add('c-c')
        @self.kb.add('q')
        def _(event):
            self.running = False
            event.app.exit()

        @self.kb.add('enter')
        def _(event):
            if self.message_buffer.text:
                self._send_message(self.message_buffer.text)
                self.message_buffer.text = ""

    def _setup_styles(self):
        self.style = Style.from_dict({
            'username': '#00aa00 bold',  # Green for current user
            'peer': '#0000ff bold',      # Blue for other users
            'timestamp': '#888888',
            'prompt': '#ff0000',
        })

    def _format_messages(self):
        text = []
        for msg in sorted(self.messages, key=lambda m: m.timestamp):
            # Format timestamp
            time_str = msg.timestamp.strftime("%H:%M:%S")
            
            # Choose style based on sender
            style = 'username' if msg.sender == self.discovery.username else 'peer'
            
            # Format message line
            text.extend([
                ("class:timestamp", f"[{time_str}] "),
                (f"class:{style}", f"{msg.sender}"),
                ("", ": "),
                ("", f"{msg.content}"),
                ("", "\n")
            ])
        
        # Add input prompt if in direct message mode
        if self.recipient:
            text.extend([
                ("", "\n"),
                ("class:prompt", "Type your message (Enter to send, Ctrl-C to exit)> ")
            ])
        else:
            text.extend([
                ("", "\n"),
                ("class:prompt", "Press 'q' to exit")
            ])
            
        return text

    def _get_layout(self):
        message_window = Window(
            content=FormattedTextControl(self._format_messages),
            wrap_lines=True
        )

        if self.recipient:
            input_window = Window(
                content=BufferControl(buffer=self.message_buffer),
                height=1
            )
            return Layout(HSplit([message_window, input_window]))
        else:
            return Layout(message_window)

    def _send_message(self, content):
        if not content.strip():
            return

        if self.recipient:
            msg = self.discovery.send_message(
                recipient=self.recipient,
                title="Direct Message",  # Simple title for all messages
                content=content,
                conversation_id=str(uuid.uuid4())
            )
            if msg:
                self.messages.append(msg)

    def show_conversation(self, peer: str):
        """Show and interact with a conversation with a specific peer"""
        self.recipient = peer
        self.messages = self.discovery.list_messages(peer)
        self._show_messages()

    def show_message_list(self):
        """Show list of all messages"""
        self.recipient = None
        self.messages = self.discovery.list_messages()
        self._show_messages()

    def _show_messages(self):
        app = Application(
            layout=self._get_layout(),
            key_bindings=self.kb,
            full_screen=True,
            style=self.style,
            mouse_support=True
        )

        # Clear screen and show UI
        clear()
        app.run()
        clear()

def send_new_message(discovery, recipient: str):
    """Start a direct message session with a recipient"""
    view = MessageView(discovery, recipient)
    view.show_conversation(recipient)