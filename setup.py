#!/usr/bin/env python3
"""Setup script for the Proposal Bot system."""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

def run_command(command: str, description: str) -> bool:
    """Run a shell command and return success status."""
    print(f"\n{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed:")
        print(f"Error: {e.stderr}")
        return False

def main():
    """Main setup function."""
    print("🚀 Setting up Multi-Agent Market Research Proposal Generator")
    print("=" * 60)

    # Check Python version
    if sys.version_info < (3, 11):
        print("✗ Python 3.11+ is required")
        sys.exit(1)

    print(f"✓ Python {sys.version.split()[0]} detected")

    # Check if we're in the right directory
    if not Path("requirements.txt").exists():
        print("✗ Please run this script from the project root directory")
        sys.exit(1)

    # Install dependencies
    if not run_command("pip install -r requirements.txt", "Installing Python dependencies"):
        sys.exit(1)

    # Create .env file if it doesn't exist
    if not Path(".env").exists():
        print("\n📝 Creating .env file from template...")
        if Path("env.template").exists():
            with open("env.template", "r") as template, open(".env", "w") as env_file:
                env_file.write(template.read())
            print("✓ Created .env file - please edit it with your API keys")
        else:
            print("⚠ env.template not found - please create .env manually")

    print("\n📋 Next steps:")
    print("1. Edit .env file with your API keys and configuration")
    print("2. Set up PostgreSQL database with pgvector extension:")
    print("   createdb proposal_bot")
    print("   psql proposal_bot -c 'CREATE EXTENSION vector;'")
    print("3. Start Redis server")
    print("4. Run the application:")
    print("   python main.py")
    print("5. In another terminal, start the Celery worker:")
    print("   celery -A app.core.celery_app worker --loglevel=info")
    print("6. In another terminal, start the Celery beat scheduler:")
    print("   celery -A app.core.celery_app beat --loglevel=info")

    print("\n🔗 API Endpoints:")
    print("- Main API: http://localhost:8000")
    print("- Health check: http://localhost:8000/health")
    print("- Detailed health: http://localhost:8000/health/detailed")
    print("- Metrics: http://localhost:8000/metrics")
    print("- System status: http://localhost:8000/status")
    print("- API docs: http://localhost:8000/docs")

    print("\n📊 Monitoring:")
    print("- Logs are written to stdout with structured JSON format")
    print("- Metrics available at /metrics endpoint")
    print("- Health checks available at /health endpoints")

    print("\n🎯 System is ready! Configure your .env file and start the services.")

if __name__ == "__main__":
    main()
