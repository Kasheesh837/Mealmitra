#!/usr/bin/env python3
"""
Run script for Annasamarpan application
This script starts the Flask development server
"""

import os
import sys
from app import app

if __name__ == '__main__':
    # Check if MongoDB is running
    try:
        from pymongo import MongoClient
        client = MongoClient('mongodb://localhost:27017/')
        client.admin.command('ping')
        print("✅ MongoDB connection successful")
    except Exception as e:
        print("❌ MongoDB connection failed!")
        print("Please make sure MongoDB is running on localhost:27017")
        print("Error:", str(e))
        sys.exit(1)
    
    # Start the Flask application
    print("🚀 Starting Annasamarpan application...")
    print("📱 Access the application at: http://localhost:5000")
    print("🔑 Admin login: admin@annasamarpan.com / admin123")
    print("🛑 Press Ctrl+C to stop the server")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
