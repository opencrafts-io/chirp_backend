#!/usr/bin/env python3
"""
Simple WebSocket connection test for Chirp
"""

import asyncio
import websockets
import json

async def test_websocket():
    """Test WebSocket connection to local server"""
    # Test JWT token created with local secret
    jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL3ZlcmlzYWZlLm9wZW5jcmFmdHMuaW8vIiwic3ViIjoiNmZkZDU4N2YtZDFkZC00OWFmLTljMTctYTcwOTYxMjI5N2ViIiwiYXVkIjpbImh0dHBzOi8vYWNhZGVtaWEub3BlbmNyYWZ0cy5pby8iXSwiZXhwIjoxNzU2NDE5Mjg4LCJpYXQiOjE3NTY0MTU2ODh9.b3Y4fCRgQbuGgSsuH6RJKDzzXTdg3W-Ox7qMHqcZLlk"

    uri = f"ws://localhost:8000/ws/chat/?token={jwt_token}"

    try:
        print(f"🔌 Attempting to connect to WebSocket endpoint")
        print(f"🔑 Using test JWT token: {jwt_token[:50]}...")

        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connection established!")

            # Send a test message
            test_message = {
                "type": "heartbeat",
                "timestamp": "test"
            }

            print(f"📤 Sending test message: {test_message}")
            await websocket.send(json.dumps(test_message))

            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"📥 Received response: {response}")
            except asyncio.TimeoutError:
                print("⏰ No response received within 5 seconds")

            print("✅ WebSocket test completed successfully!")

    except websockets.exceptions.InvalidURI as e:
        print(f"❌ Invalid URI: {e}")
    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ Connection closed: {e}")
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ Invalid status code: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    print("🚀 Starting WebSocket connection test...")
    print("⚠️  Note: This test uses a locally generated JWT token")
    asyncio.run(test_websocket())
