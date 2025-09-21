#!/usr/bin/env python3
"""
ESP32 WebSocket Test Client

This script connects to the ESP32 WebSocket server and displays
real-time sensor data. Useful for testing and debugging.

Usage:
    python test_websocket.py [ESP32_IP_ADDRESS]

Example:
    python test_websocket.py 192.168.1.100
"""

import asyncio
import websockets
import json
import sys
import time
from datetime import datetime

class ESP32WebSocketClient:
    def __init__(self, esp32_ip="192.168.1.100", ws_port=81, http_port=80):
        self.esp32_ip = esp32_ip
        self.ws_port = ws_port
        self.http_port = http_port
        self.ws_url = f"ws://{esp32_ip}:{ws_port}"
        self.http_url = f"http://{esp32_ip}:{http_port}"
        self.websocket = None
        self.running = False
        
    async def connect(self):
        """Connect to ESP32 WebSocket server"""
        try:
            print(f"🔌 Connecting to ESP32 WebSocket server at {self.ws_url}")
            self.websocket = await websockets.connect(self.ws_url)
            self.running = True
            print("✅ Connected successfully!")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    async def listen(self):
        """Listen for messages from ESP32"""
        if not self.websocket:
            print("❌ Not connected to WebSocket")
            return
            
        try:
            async for message in self.websocket:
                await self.handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            print("🔌 Connection closed")
            self.running = False
        except Exception as e:
            print(f"❌ Error receiving message: {e}")
            self.running = False
    
    async def handle_message(self, message):
        """Handle incoming WebSocket message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if isinstance(message, bytes):
            print(f"[{timestamp}] 📦 Binary data received: {len(message)} bytes")
            # Try to decode as Protocol Buffer if needed
            # For now, just display the raw bytes
            print(f"         Raw bytes: {message.hex()}")
        else:
            try:
                # Try to parse as JSON
                data = json.loads(message)
                temp = data.get('temperature', 'N/A')
                humidity = data.get('humidity', 'N/A')
                device_id = data.get('device_id', 'Unknown')
                
                print(f"[{timestamp}] 🌡️  Temperature: {temp}°C")
                print(f"[{timestamp}] 💧 Humidity: {humidity}%")
                print(f"[{timestamp}] 🏷️  Device: {device_id}")
                print("-" * 50)
                
            except json.JSONDecodeError:
                print(f"[{timestamp}] 📝 Text message: {message}")
    
    async def send_test_message(self, message="Hello from Python client!"):
        """Send a test message to ESP32"""
        if self.websocket:
            await self.websocket.send(message)
            print(f"📤 Sent: {message}")
        else:
            print("❌ Not connected")
    
    async def close(self):
        """Close WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            print("🔌 Connection closed")

async def test_http_endpoint(esp32_ip):
    """Test HTTP endpoint"""
    import aiohttp
    
    url = f"http://{esp32_ip}/sensor"
    print(f"🌐 Testing HTTP endpoint: {url}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ HTTP endpoint working!")
                    print(f"   Temperature: {data.get('temperature', 'N/A')}°C")
                    print(f"   Humidity: {data.get('humidity', 'N/A')}%")
                    print(f"   Device ID: {data.get('device_id', 'N/A')}")
                else:
                    print(f"❌ HTTP error: {response.status}")
    except Exception as e:
        print(f"❌ HTTP test failed: {e}")

async def main():
    # Get ESP32 IP from command line or use default
    esp32_ip = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.100"
    
    print("=" * 60)
    print("🧪 ESP32 WebSocket Test Client")
    print("=" * 60)
    print(f"ESP32 IP: {esp32_ip}")
    print("Commands:")
    print("  - Press Enter to send test message")
    print("  - Type 'quit' or 'exit' to close")
    print("  - Type 'http' to test HTTP endpoint")
    print("=" * 60)
    
    # Test HTTP endpoint first
    await test_http_endpoint(esp32_ip)
    print()
    
    # Create WebSocket client
    client = ESP32WebSocketClient(esp32_ip)
    
    # Connect to WebSocket
    if not await client.connect():
        return
    
    # Start listening task
    listen_task = asyncio.create_task(client.listen())
    
    # Interactive loop
    try:
        while client.running:
            # Check if user input is available (non-blocking)
            user_input = await asyncio.to_thread(input, "")
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            elif user_input.lower() == 'http':
                await test_http_endpoint(esp32_ip)
            elif user_input.strip() == '':
                await client.send_test_message()
            else:
                await client.send_test_message(user_input)
                
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except EOFError:
        print("\n🛑 EOF received")
    finally:
        # Cleanup
        listen_task.cancel()
        await client.close()
        print("👋 Goodbye!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Program interrupted")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)