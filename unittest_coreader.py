import unittest
import asyncio
import websockets
import json
import requests

class TestRelayServer(unittest.TestCase):
    def setUp(self):
        # Set up any necessary state or connections before each test case
        self.websocket_uri = 'ws://localhost:8765'
        self.upload_uri = 'http://localhost:8080/upload'
        self.websocket = None

    async def connect_websocket(self):
        self.websocket = await websockets.connect(self.websocket_uri)

    async def disconnect_websocket(self):
        if self.websocket:
            await self.websocket.close()

    async def send_message(self, message):
        await self.websocket.send(json.dumps(message))

    async def receive_message(self):
        return await self.websocket.recv()

    async def test_websocket_connection(self):
        await self.connect_websocket()
        self.assertTrue(self.websocket.open)

    async def test_file_upload(self):
        # Simulate file upload
        with open('test.pdf', 'rb') as f:
            files = {'file': f}
            response = requests.post(self.upload_uri, files=files)
        
        # Assert response
        self.assertEqual(response.status_code, 200)
        self.assertIn('PDF uploaded successfully', response.text)

    async def test_message_exchange(self):
        await self.connect_websocket()

        # Simulate sending and receiving messages
        message = {'type': 'ready', 'ready': True}
        await self.send_message(message)
        response = await self.receive_message()
        response_data = json.loads(response)
        
        # Assert response data
        self.assertEqual(response_data['type'], 'peer_update')
        self.assertEqual(response_data['count'], 1)

    async def tearDown(self):
        await self.disconnect_websocket()

if __name__ == '__main__':
    unittest.main()


