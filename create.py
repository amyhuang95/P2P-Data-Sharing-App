import argparse
import uuid
from lanshare.config.settings import Config
from lanshare.core.udp_discovery import UDPPeerDiscovery
from lanshare.ui.session import InteractiveSession

def generate_user_id(username):
    # Generate a short random ID (first 4 characters of a UUID)
    random_id = str(uuid.uuid4())[:4]
    return f"{username}#{random_id}"

def main():
    parser = argparse.ArgumentParser(description='LAN Peer Discovery Service')
    parser.add_argument('command', choices=['create'], help='Command to execute')
    parser.add_argument('--username', help='Username for the peer', required=False)
    
    args = parser.parse_args()
    
    if args.command == 'create':
        if not args.username:
            parser.error("Username is required for 'create' command")
        
        # Generate username with random ID
        username_with_id = generate_user_id(args.username)
        
        config = Config()
        discovery = UDPPeerDiscovery(username_with_id, config)
        discovery.start()
        
        session = InteractiveSession(discovery)
        session.start()

if __name__ == "__main__":
    main()