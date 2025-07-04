import uvicorn
from presentation.api.app import app
import os
import socket
import sys
from infrastructure.logging.config import configure_logging, log_startup_environment

def is_port_in_use(port):
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def find_available_port(start_port, max_attempts=10):
    """Find an available port starting from start_port."""
    for port_offset in range(max_attempts):
        port = start_port + port_offset
        if not is_port_in_use(port):
            return port
    return None

if __name__ == "__main__":
    # Configure logging
    configure_logging()
    log_startup_environment()

    # Use port from environment variable if available, otherwise use 8889
    default_port = int(os.environ.get("PORT", 8889))

    # Check if the port is already in use
    if is_port_in_use(default_port):
        print(f"Port {default_port} is already in use. Trying to find an available port...")
        port = find_available_port(default_port + 1)
        if port:
            print(f"Found available port: {port}")
        else:
            print(f"Could not find an available port after trying {default_port+1} to {default_port+10}.")
            print("Please specify a different port using the PORT environment variable.")
            sys.exit(1)
    else:
        port = default_port

    print(f"Starting API server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
