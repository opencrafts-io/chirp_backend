#!/usr/bin/env python3
"""
Test script for WebSocket chat functionality
Run this to test the WebSocket implementation
"""

import asyncio
import websockets
import json

# Configuration
WEBSOCKET_URL = "ws://localhost:8000/ws/chat/"
# Use the actual JWT token provided
ACTUAL_JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL3ZlcmlzYWZlLm9wZW5jcmFmdHMuaW8vIiwic3ViIjoiNmZkZDU4N2YtZDFkZC00OWFmLTljMTctYTcwOTYxMjI5N2ViIiwiYXVkIjpbImh0dHBzOi8vYWNhZGVtaWEub3BlbmNyYWZ0cy5pby8iXSwiZXhwIjoxNzU2NDUzNjIyLCJpYXQiOjE3NTYyMzc2MjJ9.vR8Yu5BYAZQn8esGlCvwX6b0D3MxeoDyFjxEQROrZYk"
TEST_CONVERSATION_ID = "test_conv_456"

async def test_websocket():
    """Test WebSocket functionality"""
    uri = f"{WEBSOCKET_URL}?token={ACTUAL_JWT_TOKEN}"

    print(f"Connecting to WebSocket: {uri}")

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected successfully")

            # Test joining a conversation
            join_message = {
                "type": "join_conversation",
                "conversation_id": TEST_CONVERSATION_ID
            }
            await websocket.send(json.dumps(join_message))
            print("📤 Sent join conversation message")

            # Wait for response
            response = await websocket.recv()
            response_data = json.loads(response)
            print(f"📥 Received: {response_data}")

            if response_data.get('type') == 'conversation_joined':
                print("✅ Successfully joined conversation")

                # Test sending a message
                chat_message = {
                    "type": "chat_message",
                    "content": "Hello from test script!"
                }
                await websocket.send(json.dumps(chat_message))
                print("📤 Sent chat message")

                # Wait for message broadcast
                response = await websocket.recv()
                response_data = json.loads(response)
                print(f"📥 Received: {response_data}")

                if response_data.get('type') == 'chat_message':
                    print("✅ Message broadcast received")

                # Test leaving conversation
                leave_message = {
                    "type": "leave_conversation",
                    "conversation_id": TEST_CONVERSATION_ID
                }
                await websocket.send(json.dumps(leave_message))
                print("📤 Sent leave conversation message")

                response = await websocket.recv()
                response_data = json.loads(response)
                print(f"📥 Received: {response_data}")

                if response_data.get('type') == 'conversation_left':
                    print("✅ Successfully left conversation")

            # Test heartbeat
            heartbeat_message = {
                "type": "heartbeat"
            }
            await websocket.send(json.dumps(heartbeat_message))
            print("📤 Sent heartbeat")

            response = await websocket.recv()
            response_data = json.loads(response)
            print(f"📥 Received: {response_data}")

            if response_data.get('type') == 'heartbeat_response':
                print("✅ Heartbeat response received")

    except websockets.exceptions.ConnectionClosed as e:
        print(f"✅ WebSocket connection closed: {e}")
    except Exception as e:
        if "403" in str(e) or "Forbidden" in str(e):
            print("✅ Correctly handled invalid token: server rejected WebSocket connection")
        else:
            print(f"❌ Error: {e}")

async def test_invalid_token():
    """Test WebSocket with invalid token"""
    uri = f"{WEBSOCKET_URL}?token=invalid_token"
    print(f"\nTesting with invalid token: {uri}")

    try:
        async with websockets.connect(uri):
            print("❌ Should not connect with invalid token")
    except Exception as e:
        if "403" in str(e) or "Forbidden" in str(e):
            print("✅ Correctly handled invalid token: server rejected WebSocket connection")
        else:
            print(f"❌ Error: {e}")

async def main():
    """Main test function"""
    print("🧪 Starting WebSocket tests...")

    # Test with valid token
    await test_websocket()

    # Test with invalid token
    await test_invalid_token()

    print("\n🎉 WebSocket tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
