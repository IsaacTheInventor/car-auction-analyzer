#!/usr/bin/env python3
"""
HTTPS Server for Car Auction Analyzer Camera Test

This script creates a secure HTTPS server with self-signed certificates
to allow camera access on iPhone Safari. iPhone requires HTTPS for
camera API access when connecting over a network.

Usage:
    python https-server.py

Then on your iPhone:
    1. Open Safari and go to https://<your-computer-ip>
    2. Accept the security warning about the self-signed certificate
    3. Navigate to camera-simple.html
    4. Tap "Start Camera Test" and allow camera access when prompted
"""

import http.server
import ssl
import socket
import os
import webbrowser
import subprocess
import sys
from pathlib import Path
import platform

# Configuration
PORT = 443  # Standard HTTPS port
DIRECTORY = Path(__file__).parent  # Use the directory where this script is located
CERT_FILE = DIRECTORY / "server.crt"
KEY_FILE = DIRECTORY / "server.key"

def get_local_ip():
    """Get the local IP address of this machine."""
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

def generate_self_signed_cert(cert_file, key_file, ip_address):
    """Generate a self-signed certificate for HTTPS."""
    print("Generating self-signed certificate...")
    
    # Create OpenSSL configuration with IP address as Subject Alternative Name
    openssl_config = f"""[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = Car Auction Analyzer

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
IP.1 = {ip_address}
DNS.1 = localhost
"""
    
    # Write OpenSSL config to temporary file
    config_file = DIRECTORY / "openssl.cnf"
    with open(config_file, 'w') as f:
        f.write(openssl_config)
    
    try:
        # Generate private key and certificate
        subprocess.run([
            'openssl', 'req', '-x509', '-nodes',
            '-days', '365',
            '-newkey', 'rsa:2048',
            '-keyout', str(key_file),
            '-out', str(cert_file),
            '-config', str(config_file)
        ], check=True)
        print(f"Certificate generated successfully: {cert_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error generating certificate: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("OpenSSL not found. Please install OpenSSL to generate certificates.")
        print("Alternatively, you can manually generate certificates with:")
        print(f"openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout {key_file} -out {cert_file}")
        sys.exit(1)
    finally:
        # Clean up config file
        if os.path.exists(config_file):
            os.remove(config_file)

def check_admin():
    """Check if the script is running with administrator privileges."""
    try:
        if platform.system() == 'Windows':
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:  # Unix-based systems
            return os.geteuid() == 0
    except:
        return False

def main():
    # Get local IP address
    local_ip = get_local_ip()
    
    # Check if running as admin for port 443
    if PORT < 1024 and not check_admin():
        print("=" * 70)
        print("ERROR: Administrator privileges required for port 443")
        print("=" * 70)
        print("\nPlease run this script as administrator/root to use port 443.")
        print("Windows: Right-click Command Prompt/PowerShell and select 'Run as administrator'")
        print("macOS/Linux: Use 'sudo python https-server.py'")
        print("\nAlternatively, edit this script to use a port number above 1024 (e.g., 8443)")
        print("=" * 70)
        sys.exit(1)
    
    # Generate certificate if it doesn't exist
    if not os.path.exists(CERT_FILE) or not os.path.exists(KEY_FILE):
        generate_self_signed_cert(CERT_FILE, KEY_FILE, local_ip)
    
    # Change to the directory containing the HTML files
    os.chdir(DIRECTORY)
    
    # Create the HTTPS server
    handler = http.server.SimpleHTTPRequestHandler
    httpd = http.server.HTTPServer(("", PORT), handler)
    
    # Add SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    
    # Print instructions
    print("\n" + "=" * 70)
    print("Car Auction Analyzer HTTPS Camera Server")
    print("=" * 70)
    print(f"\nServer running at: https://{local_ip}:{PORT}")
    print("\nOn your iPhone, open Safari and go to:")
    print(f"  https://{local_ip}")
    print("\nIMPORTANT: You will see a security warning about the certificate.")
    print("1. Tap 'Show Details' or 'Advanced'")
    print("2. Tap 'Visit This Website' or similar option")
    print("3. Tap 'Continue' to accept the risk")
    print("4. Once loaded, navigate to 'camera-simple.html'")
    print("5. Tap 'Start Camera Test' and allow camera access when prompted")
    print("\nMake sure your iPhone is connected to the same WiFi network as this computer.")
    print("\nPress Ctrl+C to stop the server.")
    print("=" * 70 + "\n")
    
    # Try to open the browser automatically
    camera_url = f"https://{local_ip}/camera-simple.html"
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

if __name__ == "__main__":
    main()
