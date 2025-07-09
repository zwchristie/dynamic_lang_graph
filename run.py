#!/usr/bin/env python3
"""
Startup script for the Agentic Workflow System.
This script allows easy switching between different environments.
"""

import os
import sys
import argparse
from pathlib import Path

def check_environment_files():
    """Check if environment files exist"""
    env_files = ["env.local", "env.dev", "env.testing"]
    missing_files = []
    
    for env_file in env_files:
        if not Path(env_file).exists():
            missing_files.append(env_file)
    
    if missing_files:
        print("⚠️  Missing environment files:")
        for file in missing_files:
            print(f"   - {file}")
        print()
        print("Please create the missing environment files or copy from env.example")
        return False
    
    return True

def check_certificates(environment):
    """Check if certificates exist for SSL environments"""
    if environment in ["dev", "testing"]:
        cert_dir = Path("./certs")
        cert_files = {
            "dev": ("dev_cert.pem", "dev_key.pem"),
            "testing": ("test_cert.pem", "test_key.pem")
        }
        
        cert_file, key_file = cert_files[environment]
        cert_path = cert_dir / cert_file
        key_path = cert_dir / key_file
        
        if not cert_path.exists() or not key_path.exists():
            print(f"⚠️  SSL certificates missing for {environment} environment:")
            print(f"   - {cert_path}")
            print(f"   - {key_path}")
            print()
            print("Run 'python generate_certs.py' to generate certificates")
            return False
    
    return True

def main():
    parser = argparse.ArgumentParser(
        description="Start the Agentic Workflow System in different environments"
    )
    parser.add_argument(
        "environment",
        choices=["local", "dev", "testing"],
        help="Environment to run the application in"
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Override host address"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Override port number"
    )
    parser.add_argument(
        "--generate-certs",
        action="store_true",
        help="Generate certificates before starting (for dev/testing)"
    )
    
    args = parser.parse_args()
    
    # Check environment files
    if not check_environment_files():
        sys.exit(1)
    
    # Generate certificates if requested
    if args.generate_certs and args.environment in ["dev", "testing"]:
        print("🔐 Generating certificates...")
        try:
            import generate_certs
            generate_certs.main()
        except ImportError:
            print("❌ Could not import generate_certs.py")
            sys.exit(1)
        print()
    
    # Check certificates for SSL environments
    if not check_certificates(args.environment):
        sys.exit(1)
    
    # Set environment variable
    os.environ["ENVIRONMENT"] = args.environment
    
    # Override host/port if specified
    if args.host:
        os.environ["HOST"] = args.host
    if args.port:
        os.environ["PORT"] = str(args.port)
    
    print(f"🚀 Starting Agentic Workflow System in {args.environment} environment...")
    print(f"   Environment: {args.environment}")
    print(f"   Host: {os.environ.get('HOST', 'default')}")
    print(f"   Port: {os.environ.get('PORT', 'default')}")
    
    if args.environment in ["dev", "testing"]:
        print(f"   SSL: Enabled")
    else:
        print(f"   SSL: Disabled")
    
    print()
    
    # Import and run the application
    try:
        from app.main import app, settings
        import uvicorn
        
        # Get SSL context if available
        ssl_context = settings.ssl_context
        
        # Run with SSL if certificates are available
        if ssl_context:
            print(f"🔒 Starting server with SSL on {settings.host}:{settings.port}")
            uvicorn.run(
                app, 
                host=settings.host, 
                port=settings.port,
                **ssl_context
            )
        else:
            print(f"🌐 Starting server without SSL on {settings.host}:{settings.port}")
            uvicorn.run(
                app, 
                host=settings.host, 
                port=settings.port
            )
            
    except ImportError as e:
        print(f"❌ Error importing application: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 