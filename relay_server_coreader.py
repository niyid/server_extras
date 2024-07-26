import asyncio
import websockets
import json
import ssl
import os
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from datetime import datetime, timedelta
import pymupdf  # PyMuPDF

class RelayServer:
    def __init__(self):
        self.sessions = {}
        self.clients = {}

    async def register(self, websocket, device_id, session_id, title):
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                'title': title,
                'peers': {},
                'current_page': 0,
                'current_paragraph': 0,
            }
        self.sessions[session_id]['peers'][device_id] = {'websocket': websocket, 'ready': False}
        self.clients[websocket] = {'device_id': device_id, 'session_id': session_id}
        await self.notify_peers(session_id)

    async def unregister(self, websocket):
        if websocket in self.clients:
            device_id = self.clients[websocket]['device_id']
            session_id = self.clients[websocket]['session_id']
            del self.clients[websocket]
            del self.sessions[session_id]['peers'][device_id]
            if not self.sessions[session_id]['peers']:
                del self.sessions[session_id]
            else:
                await self.notify_peers(session_id)

    async def handle_ready(self, websocket, data):
        session_id = data['session_id']
        device_id = data['device_id']
        self.sessions[session_id]['peers'][device_id]['ready'] = data['ready']
        if all(peer['ready'] for peer in self.sessions[session_id]['peers'].values()):
            await self.notify_paragraph_turn(session_id)

    async def notify_peers(self, session_id):
        session = self.sessions[session_id]
        message = json.dumps({
            'type': 'peer_update',
            'title': session['title'],
            'count': len(session['peers']),
            'page': session['current_page'],
            'paragraph': session['current_paragraph'],
        })
        await asyncio.wait([peer['websocket'].send(message) for peer in session['peers'].values()])

    async def notify_paragraph_turn(self, session_id):
        session = self.sessions[session_id]
        paragraphs = self.extract_paragraphs(session_id, session['current_page'])
        if session['current_paragraph'] < len(paragraphs) - 1:
            session['current_paragraph'] += 1
        else:
            session['current_paragraph'] = 0
            session['current_page'] += 1
        message = json.dumps({
            'type': 'turn_paragraph',
            'page': session['current_page'],
            'paragraph': session['current_paragraph'],
        })
        await asyncio.wait([peer['websocket'].send(message) for peer in session['peers'].values()])

    def extract_paragraphs(self, session_id, page_number):
        pdf_path = f"/home/niyid/workspace/pdf/{session_id}.pdf"
        doc = pymupdf.open(pdf_path)
        page = doc.load_page(page_number)
        text = page.get_text("text")
        paragraphs = text.split("\n\n")
        return [p.strip() for p in paragraphs if p.strip()]

relay_server = RelayServer()
async def handle_connection(self, websocket, path):
    try:
        async for message in websocket:
            data = json.loads(message)
            if data["type"] == "register":
                await relay_server.register(websocket, data["device_id"], data["session_id"], data["title"])
            elif data["type"] == "ready":
                await relay_server.handle_ready(websocket, data)
    except websockets.exceptions.ConnectionClosedError:
        pass
    finally:
        await self.unregister(websocket)

async def main():
    key_file_path = "/home/niyid/workspace/coreader.key"
    crt_file_path = "/home/niyid/workspace/coreader.crt"

    try:
        with open(key_file_path, "rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=b'',  # Replace 'your_passphrase_here' with your passphrase
                backend=default_backend()
            )

        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(crt_file_path, keyfile=key_file_path, password="")
        print("Certificate and key loaded successfully from:", key_file_path)

    except FileNotFoundError:
        print("Error: File not found at path:", key_file_path)
    except Exception as e:
        print("An error occurred:", e)
    
    async with websockets.serve(handle_connection, "0.0.0.0", 8765, ssl=ssl_context):
        print(f"Server running on port 8765")
        while True:
            print(f"Daemons run here...")
            await asyncio.sleep(2 * 24 * 3600)

asyncio.run(main())

