import socket
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.shortcuts import clear

from ..core.discovery import PeerDiscovery
from .debug_view import DebugView
from .user_list_view import UserListView

class InteractiveSession:
    def __init__(self, discovery: PeerDiscovery):
        self.discovery = discovery
        self.commands = {
            'ul': self._show_user_list,
            'debug': self._show_debug_view,
            'help': self.show_help,
            'clear': self.clear_screen,
            'exit': self.exit_session,
            'quit': self.exit_session
        }
        self.running = True
        self._setup_prompt()

    def _setup_prompt(self):
        """Setup the prompt session"""
        self.style = Style.from_dict({
            'username': '#00aa00 bold',
            'at': '#888888',
            'colon': '#888888',
            'pound': '#888888',
        })
        
        self.completer = WordCompleter(list(self.commands.keys()))
        
        self.session = PromptSession(
            completer=self.completer,
            style=self.style,
            complete_while_typing=True
        )

    def _show_user_list(self, *args):
        """Show the user list view"""
        view = UserListView(self.discovery)
        view.show()

    def _show_debug_view(self, *args):
        """Show the debug view"""
        view = DebugView(self.discovery)
        view.show()

    def show_help(self, *args):
        """Show help message"""
        print("\nAvailable commands:")
        print("  ul     - List online users")
        print("  debug  - Toggle debug mode")
        print("  clear  - Clear screen")
        print("  help   - Show this help message")
        print("  exit   - Exit the session")

    def clear_screen(self, *args):
        """Clear the terminal screen"""
        clear()

    def exit_session(self, *args):
        """Exit the session"""
        self.running = False
        return True

    def get_prompt_text(self):
        """Get the formatted prompt text"""
        # Get local IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't need to be reachable, just to get local IP
            s.connect(('10.255.255.255', 1))
            local_ip = s.getsockname()[0]
        except Exception:
            local_ip = '127.0.0.1'
        finally:
            s.close()

        return HTML(
            f'<username>{self.discovery.username}</username>'
            f'<at>@</at>'
            f'<colon>LAN</colon>'
            f'<colon>({local_ip})</colon>'
            f'<pound># </pound>'
        )

    def handle_command(self, command_line):
        """Handle a command input"""
        if not command_line:
            return False
            
        parts = command_line.strip().split()
        command = parts[0].lower()
        args = parts[1:]

        if command in self.commands:
            return self.commands[command](*args)
        else:
            print(f"Unknown command: {command}")
            print("Type 'help' for available commands")
            return False

    def start(self):
        """Start the interactive session"""
        clear()
        print(f"\nWelcome to LAN Share, {self.discovery.username}!")
        print("Type 'help' for available commands")
        
        while self.running:
            try:
                command = self.session.prompt(self.get_prompt_text())
                self.handle_command(command)
            except KeyboardInterrupt:
                print("\nUse 'exit' to quit")
            except EOFError:
                break
            except Exception as e:
                print(f"Error: {e}")

        # Cleanup
        self.discovery.cleanup()