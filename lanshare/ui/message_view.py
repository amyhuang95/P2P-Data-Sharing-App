from prompt_toolkit.application import Application
from prompt_toolkit.layout.containers import Window, HSplit
from prompt_toolkit.layout.controls import FormattedTextControl, BufferControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.styles import Style
from prompt_toolkit.shortcuts import clear
from datetime import datetime
from typing import List, Optional, Dict
import threading
import time
import uuid

from ..core.types import Message

class MessageView:
    def __init__(self, discovery, recipient=None):
        self.discovery = discovery
        self.recipient = recipient
        self.running = True
        self.messages: List[Message] = []
        self.message_buffer = Buffer()
        self.last_check = datetime.now()
        
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
            'username': '#00aa00 bold',    # Green for current user
            'peer': '#0000ff bold',        # Blue for other users
            'timestamp': '#888888',        # Gray for timestamp
            'prompt': '#ff0000',           # Red for prompt
            'info': '#888888 italic',      # Gray italic for info
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
                title="Direct Message",
                content=content,
                conversation_id=self.current_conversation_id
            )
            if msg:
                self.messages.append(msg)

    def _check_new_messages(self):
        """Check for new messages and update display"""
        while self.running:
            if self.recipient:
                # Get all messages with this peer
                new_messages = self.discovery.list_messages(self.recipient)
                # Add only messages we haven't seen
                for msg in new_messages:
                    if msg not in self.messages:
                        self.messages.append(msg)
            time.sleep(0.1)  # Check every 100ms

    def format_conversation_list(self) -> List[Message]:
        """Format the list of conversations for display"""
        # Group messages by conversation
        conversations: Dict[str, List[Message]] = {}
        for msg in self.discovery.list_messages():
            conv_id = msg.conversation_id
            if conv_id not in conversations:
                conversations[conv_id] = []
            conversations[conv_id].append(msg)

        text = [
            ("class:prompt", "Conversations:\n"),
            ("", "─" * 60 + "\n")
        ]

        for conv_id, msgs in conversations.items():
            # Sort messages by timestamp
            msgs.sort(key=lambda m: m.timestamp)
            last_msg = msgs[-1]
            
            # Get the other participant
            other_party = last_msg.recipient if last_msg.sender == self.discovery.username else last_msg.sender
            
            text.extend([
                ("class:info", f"ID: {conv_id[:8]}... "),
                ("class:peer", f"with {other_party}"),
                ("class:timestamp", f" (Last message: {last_msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')})"),
                ("", "\n"),
                ("class:info", f"Last message: "),
                ("", f"{last_msg.content[:50]}{'...' if len(last_msg.content) > 50 else ''}\n"),
                ("", "─" * 60 + "\n")
            ])

        return text

    def show_conversation(self, peer: str, conversation_id: Optional[str] = None):
        """Show and interact with a conversation"""
        self.recipient = peer
        self.current_conversation_id = conversation_id or str(uuid.uuid4())
        
        # Get existing messages for this conversation
        if conversation_id:
            self.messages = self.discovery.get_conversation(conversation_id)
        else:
            self.messages = []

        # Start message checking thread
        check_thread = threading.Thread(target=self._check_new_messages)
        check_thread.daemon = True
        check_thread.start()

        # Show messages
        self._show_messages()

    def show_message_list(self):
        """Show list of all conversations"""
        app = Application(
            layout=Layout(
                Window(
                    content=FormattedTextControl(self.format_conversation_list),
                    wrap_lines=True
                )
            ),
            key_bindings=self.kb,
            full_screen=True,
            style=self.style,
            mouse_support=True
        )

        clear()
        app.run()
        clear()

    def _show_messages(self):
        app = Application(
            layout=self._get_layout(),
            key_bindings=self.kb,
            full_screen=True,
            style=self.style,
            mouse_support=True
        )

        clear()
        app.run()
        clear()

def send_new_message(discovery, recipient: str):
    """Start a direct message session with a recipient"""
    view = MessageView(discovery, recipient)
    view.show_conversation(recipient)