#!/usr/bin/env python3
"""
Certificate generation script for development and testing environments.
This script creates self-signed certificates for local development.
"""

import os
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

def generate_self_signed_cert(common_name: str, cert_file: str, key_file: str, days: int = 365):
    """Generate a self-signed certificate using OpenSSL"""
    
    # Create certs directory if it doesn't exist
    certs_dir = Path("./certs")
    certs_dir.mkdir(exist_ok=True)
    
    cert_path = certs_dir / cert_file
    key_path = certs_dir / key_file
    
    # OpenSSL command to generate self-signed certificate
    cmd = [
        "openssl", "req", "-x509", "-newkey", "rsa:2048",
        "-keyout", str(key_path),
        "-out", str(cert_path),
        "-days", str(days),
        "-nodes",
        "-subj", f"/C=US/ST=State/L=City/O=Organization/CN={common_name}"
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"✅ Generated certificate: {cert_path}")
        print(f"✅ Generated private key: {key_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error generating certificate: {e}")
        print(f"Make sure OpenSSL is installed and available in your PATH")
        return False
    except FileNotFoundError:
        print("❌ OpenSSL not found. Please install OpenSSL first.")
        print("   - Windows: Download from https://slproweb.com/products/Win32OpenSSL.html")
        print("   - macOS: brew install openssl")
        print("   - Ubuntu/Debian: sudo apt-get install openssl")
        return False

def main():
    """Generate certificates for development and testing environments"""
    
    print("🔐 Generating self-signed certificates for development and testing...")
    print()
    
    # Generate development certificate
    print("📝 Generating development certificate...")
    dev_success = generate_self_signed_cert(
        common_name="localhost-dev",
        cert_file="dev_cert.pem",
        key_file="dev_key.pem",
        days=365
    )
    
    print()
    
    # Generate testing certificate
    print("📝 Generating testing certificate...")
    test_success = generate_self_signed_cert(
        common_name="localhost-test",
        cert_file="test_cert.pem",
        key_file="test_key.pem",
        days=365
    )
    
    print()
    
    if dev_success and test_success:
        print("🎉 All certificates generated successfully!")
        print()
        print("📁 Certificate files created:")
        print("   - ./certs/dev_cert.pem")
        print("   - ./certs/dev_key.pem")
        print("   - ./certs/test_cert.pem")
        print("   - ./certs/test_key.pem")
        print()
        print("🚀 You can now run the application with SSL:")
        print("   - Development: ENVIRONMENT=dev python -m app.main")
        print("   - Testing: ENVIRONMENT=testing python -m app.main")
        print()
        print("⚠️  Note: These are self-signed certificates for development only.")
        print("   Browsers will show security warnings - this is expected.")
    else:
        print("❌ Some certificates failed to generate. Please check the errors above.")

if __name__ == "__main__":
    main() 