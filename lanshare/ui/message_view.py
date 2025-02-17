from prompt_toolkit.application import Application
from prompt_toolkit.layout.containers import Window, HSplit, ScrollOffsets
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
        self.last_message_count = 0
        self.current_conversation_id = None
        
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
                # Force update display
                if hasattr(self, 'app'):
                    self.app.invalidate()

    def format_conversation_list(self):
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
                ("class:info", f"ID: {conv_id[:5]} "),
                ("class:peer", f"with {other_party}"),
                ("class:timestamp", f" (Last: {last_msg.timestamp.strftime('%H:%M:%S')})"),
                ("", "\n"),
                ("class:info", f"Last message: "),
                ("", f"{last_msg.content[:50]}{'...' if len(last_msg.content) > 50 else ''}\n"),
                ("", "─" * 60 + "\n")
            ])

        return text

    def show_conversation(self, peer: str, conversation_id: Optional[str] = None):
        """Show and interact with a conversation"""
        self.recipient = peer
        self.current_conversation_id = conversation_id or self.discovery._generate_conversation_id(
            self.discovery.username, peer)
        
        # Get existing messages for this conversation
        self.messages = self.discovery.get_conversation(self.current_conversation_id)
        self.last_message_count = len(self.messages)

        # Show messages UI
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

    def _check_new_messages(self):
        """Check for new messages and update display"""
        while self.running:
            if self.recipient and self.current_conversation_id:
                # Get all messages for this conversation
                new_messages = self.discovery.get_conversation(self.current_conversation_id)
                if len(new_messages) > self.last_message_count:
                    self.messages = new_messages
                    self.last_message_count = len(new_messages)
                    # Force refresh of the display
                    if hasattr(self, 'app'):
                        self.app.invalidate()
            time.sleep(0.1)  # Check every 100ms

    def _show_messages(self):
        """Display messages in the UI"""
        # Create auto-scrolling message window
        message_window = Window(
            content=FormattedTextControl(
                self._format_messages,
                focusable=False  # Make message window not focusable
            ),
            wrap_lines=True,
            always_hide_cursor=True,
            scroll_offsets=ScrollOffsets(top=1, bottom=1),
            allow_scroll_beyond_bottom=False
        )

        # Add input window if in conversation mode
        if self.recipient:
            input_window = Window(
                content=BufferControl(
                    buffer=self.message_buffer,
                    focusable=True
                ),
                height=1,
                dont_extend_height=True
            )
            layout = Layout(HSplit([
                message_window,
                input_window
            ]))
            # Ensure input window gets focus
            layout.focus(input_window)
        else:
            layout = Layout(message_window)

        # Create and configure the application
        self.app = Application(
            layout=layout,
            key_bindings=self.kb,
            full_screen=True,
            style=self.style,
            mouse_support=True,
            erase_when_done=True
        )

        # Clear screen
        clear()
        
        # Start message checking thread
        check_thread = threading.Thread(target=self._check_new_messages)
        check_thread.daemon = True
        check_thread.start()
        
        # Start refresh thread
        def refresh_screen():
            while self.running:
                self.app.invalidate()
                time.sleep(0.1)

        refresh_thread = threading.Thread(target=refresh_screen)
        refresh_thread.daemon = True
        refresh_thread.start()

        try:
            self.app.run()
        finally:
            self.running = False
            clear()

def send_new_message(discovery, recipient: str):
    """Start a direct message session with a recipient"""
    view = MessageView(discovery, recipient)
    view.show_conversation(recipient)