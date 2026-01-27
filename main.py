import webview
import subprocess
import time
import os
import sys

def start_server():
    """Starts the FastAPI server in a separate process."""
    cmd = [sys.executable, "server.py"]
    return subprocess.Popen(cmd)

if __name__ == "__main__":
    # Start the backend server
    server_process = start_server()
    
    # Wait a moment for server to start
    time.sleep(2)
    
    # Load the index.html
    current_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(current_dir, "index.html")
    
    # Create the overlay window
    # We set transparent=True and frameless=True for the overlay effect
    # easy_drag=True allows moving the window by clicking anywhere
    window = webview.create_window(
        'AI Agent Overlay',
        html_path,
        width=420,
        height=800,
        x=1000, # More conservative position for different resolutions
        y=50,
        frameless=True,
        easy_drag=True,
        transparent=True,
        on_top=True
    )
    
    try:
        webview.start()
    finally:
        # Cleanup server process on exit
        server_process.terminate()
