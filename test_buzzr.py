import asyncio
import websockets
import json
import uuid
import hashlib
import geohash2
import ssl

def sha256_encode(string):
    # Encode the string as bytes
    encoded_string = string.encode('utf-8')
    # Compute the SHA-256 hash
    sha256_hash = hashlib.sha256(encoded_string).hexdigest()
    return sha256_hash
    
def encode_lat_lon(latitude, longitude, precision=8):
    # Encode latitude and longitude as a geohash
    geohash = geohash2.encode(latitude, longitude, precision=precision)
    return geohash    
    
import asyncio

async def send_message():
    async with websockets.connect('ws://8.222.202.85:7071') as websocket:
        # Send a registration message to the server
        action = 'register'
        device_id = sha256_encode('+2348095829403')
        geohash = encode_lat_lon(6.4474, 3.3903)
        new_geohash = encode_lat_lon(6.497988, 3.343929)

        message_data = {"action": action, "geohash": geohash, "device_id": device_id}
        await websocket.send(json.dumps(message_data))
        print(f"Registration sent")

        # Send a broadcast message to the server
        action = 'broadcast'
        message_text = 'Bloodbath @ Lobster Close!'
        message_data = {"action": action, "device_id": device_id, "geohash": geohash, "message": message_text}
        await websocket.send(json.dumps(message_data))
        print(f"Broadcast sent")
        
        # Receive message_id after calling broadcast()
        broadcast_response = await websocket.recv()
        print(f"Message ID received")
        broadcast_response_data = json.loads(broadcast_response)
        message_id = broadcast_response_data.get("message_id")
        if message_id:
            print(f"Received message_id: {message_id}")
            # Send a rebroadcast message to the server using the received message_id
            action = 'rebroadcast'
            message_data = {"action": action, "device_id": device_id, "geohash": geohash, "message_id": str(message_id)}
            await websocket.send(json.dumps(message_data))
            print(f"Rebroadcast sent")
        else:
            print("Failed to receive message_id")
                
        action = 'update_location'
        message_data = {"action": action, "device_id": device_id, "old_geohash": geohash, "new_geohash": new_geohash}
        await websocket.send(json.dumps(message_data))
        print(f"Location update sent")

        # Receive and handle messages from the server
        while True:
            message = await websocket.recv()
            print(f"Received message from server: {message}")

# Call the function to send messages
asyncio.run(send_message())