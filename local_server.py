import http.server
import socketserver
import os
import config

# --- Configuration ---
PORT = config.LOCAL_SERVER_PORT
DIRECTORY = config.PUBLIC_FILES_DIR

# --- Server Handler ---
# We use functools.partial to change the directory of the SimpleHTTPRequestHandler
# as recommended in the official Python documentation.
class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

# --- Main Server Logic ---
def run_server():
    """
    Starts a simple HTTP server to serve files from the public directory.
    """
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        # Ensure the directory exists
        if not os.path.isdir(DIRECTORY):
            print(f"Error: Public directory '{DIRECTORY}' not found.")
            print("Please create it or check your .env configuration.")
            return

        print("--- Local File Server ---")
        print(f"Serving files from directory: ./{DIRECTORY}")
        print(f"Access your files at: http://localhost:{PORT}")
        print("-------------------------")
        print("Press Ctrl+C to stop the server.")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
            httpd.shutdown()

if __name__ == "__main__":
    run_server()
