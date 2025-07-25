#!/usr/bin/env python3
"""
Simple HTTP Server for Car Auction Analyzer Camera Test

This script starts a simple HTTP server that serves the camera-test.html file
over your local network, allowing you to access it from your iPhone or any
other device on the same network.

Usage:
    python serve.py

Then open your iPhone browser and navigate to:
    http://<your-computer-ip>:8000/camera-test.html
"""

import http.server
import socketserver
import socket
import os
import webbrowser
from pathlib import Path

# Configuration
PORT = 8000
DIRECTORY = Path(__file__).parent  # Use the directory where this script is located

# Get the local IP address
def get_local_ip():
    try:
        # Create a socket to determine the local IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Doesn't need to be reachable
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        # Fallback if the above method fails
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)

# Change to the directory containing the HTML file
os.chdir(DIRECTORY)

# Create the HTTP server
Handler = http.server.SimpleHTTPRequestHandler
httpd = socketserver.TCPServer(("", PORT), Handler)

# Get the local IP address
local_ip = get_local_ip()

# Print instructions
print("\n" + "=" * 70)
print("Car Auction Analyzer Camera Test Server")
print("=" * 70)
print(f"\nServer running at: http://{local_ip}:{PORT}")
print("\nOn your iPhone, open Safari and go to:")
print(f"  http://{local_ip}:{PORT}/camera-test.html")
print("\nMake sure your iPhone is connected to the same WiFi network as this computer.")
print("\nPress Ctrl+C to stop the server.")
print("=" * 70 + "\n")

# Try to open the browser automatically
camera_url = f"http://{local_ip}:{PORT}/camera-test.html"
try:
    webbrowser.open(camera_url)
    print("Opening browser automatically...")
except:
    pass  # Ignore if browser can't be opened

# Start the server
try:
    httpd.serve_forever()
except KeyboardInterrupt:
    print("\nServer stopped.")
    httpd.server_close()
