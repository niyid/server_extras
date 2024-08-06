import asyncio
import websockets
import json
import ssl
import os
import base64
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from datetime import datetime, timedelta
import pymupdf  # PyMuPDF

BASE_PDF_PATH = "/home/niyid/workspace/pdf"

class RelayServer:
    def __init__(self):
        self.sessions = {}
        self.clients = {}

    async def register(self, websocket, device_id, session_id, title):
        print(f"register {device_id} {session_id} {title}")
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                'title': title,
                'peers': {},
                'current_page': 0,
                'current_paragraph': 0,
                'file_chunks': {}
            }
        self.sessions[session_id]['peers'][device_id] = {'websocket': websocket, 'ready': False}
        self.clients[websocket] = {'device_id': device_id, 'session_id': session_id}
          
        message = json.dumps({
            'type': 'create_session_response',
            'session_id': session_id,
            'title': title
        })
        print(f"register - {message}")
        
        await websocket.send(message)

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

    async def handle_ready(self, websocket, device_id, session_id, ready):
        self.sessions[session_id]['peers'][device_id]['ready'] = ready
        if all(peer['ready'] for peer in self.sessions[session_id]['peers'].values()):
            await self.notify_page_turn(session_id)
            # Reset the 'ready' flags for all peers after the paragraph turn
            for peer in self.sessions[session_id]['peers'].values():
                peer['ready'] = False


    async def notify_peers(self, session_id):
        #print(f"notify_peers {session_id}")
        session = self.sessions[session_id]
        message = json.dumps({
            'type': 'peer_update',
            'count': len(session['peers'])
        })
        await asyncio.gather(*[peer['websocket'].send(message) for peer in session['peers'].values()])

    async def handle_upload_chunk(self, websocket, device_id, session_id, title, chunk_index, chunk_data):
        #print(f"handle_upload_chunk {device_id} {session_id} {title} {chunk_index}")
        if session_id not in self.sessions:
            await self.register(websocket, device_id, session_id, title)
        session = self.sessions[session_id]
        if session_id not in session['file_chunks']:
            session['file_chunks'][session_id] = {}
        session['file_chunks'][session_id][chunk_index] = chunk_data

    async def handle_upload_complete(self, websocket, device_id, session_id, title):
        #print(f"handle_upload_complete {device_id} {session_id} {title}")
        session = self.sessions[session_id]
        session['title'] = title
        session['lead_device_id'] = device_id
        filename = f"{session_id}.pdf"
        pdf_path = os.path.join(BASE_PDF_PATH, filename)

        with open(pdf_path, 'wb') as f:
            for i in sorted(session['file_chunks'][session_id].keys()):
                f.write(base64.b64decode(session['file_chunks'][session_id][i]))

        session['pdf_path'] = pdf_path
        del session['file_chunks'][session_id]
        print(f"File uploaded and saved to {pdf_path}")

    #on each page turn, generate the paragraphs and notify peers 
       
    async def notify_page_turn(self, session_id):
        print(f"notify_page_turn {session_id}")
        session = self.sessions[session_id]
        current_page = session['current_page']

        session['current_page'] += 1

        # Ensure the page number starts at 1, not 0
        if session['current_page'] < 1:
            session['current_page'] = 1

        message = {
            'type': 'turn_page',
            'count': len(session['peers']),
            'current_page': session['current_page']
        }

        message['page'] = self.extract_page(session_id, session['current_page'])

        message_json = json.dumps(message)

        #print(f"notify_paragraph_turn message= {message_json}")
        print(f"notify_page_turn peers= {session['peers']}")

        # Send the update to all peers in the session
        await asyncio.gather(*[peer['websocket'].send(message_json) for peer in session['peers'].values()])
        
    async def notify_paragraph_turn(self, session_id):
        print(f"notify_paragraph_turn {session_id}")
        session = self.sessions[session_id]
        current_page = session['current_page']
        current_paragraph = session['current_paragraph']

        # Check if it's a new page
        if current_paragraph == 0:
            paragraphs = self.extract_paragraphs(session_id, current_page)
        else:
            paragraphs = None

        if paragraphs is not None and current_paragraph < len(paragraphs) - 1:
            session['current_paragraph'] += 1
        else:
            session['current_paragraph'] = 0
            session['current_page'] += 1
            # Extract paragraphs only if it's a new page
            paragraphs = self.extract_paragraphs(session_id, session['current_page'])

        # Ensure the page number starts at 1, not 0
        if session['current_page'] < 1:
            session['current_page'] = 1

        message = {
            'type': 'turn_paragraph',
            'count': len(session['peers']),
            'current_page': session['current_page'],
            'current_paragraph': session['current_paragraph']
        }

        if paragraphs is not None:
            message['paragraphs'] = paragraphs
        else:
            message['paragraphs'] = ""

        # Convert the message to JSON
        message_json = json.dumps(message)

        #print(f"notify_paragraph_turn message= {message_json}")
        #print(f"notify_paragraph_turn peers= {session['peers']}")

        # Send the update to all peers in the session
        await asyncio.gather(*[peer['websocket'].send(message_json) for peer in session['peers'].values()])

    def extract_page(self, session_id, page_number):
        pdf_path = f"{BASE_PDF_PATH}/{session_id}.pdf"
        doc = pymupdf.open(pdf_path)
        page = doc.load_page(page_number - 1)  # Page numbers are zero-based
        text_dict = page.get_text("html")
        doc.close()
        return text_dict

    def extract_paragraphs(self, session_id, page_number, spacing_threshold=10, font_size_threshold=14, header_y_threshold=100, min_paragraph_length=20):
        pdf_path = f"{BASE_PDF_PATH}/{session_id}.pdf"
        doc = pymupdf.open(pdf_path)
        page = doc.load_page(page_number)
        text_dict = page.get_text("dict")
        blocks = text_dict['blocks']
        
        paragraphs = []
        current_paragraph = []
        previous_bottom = None

        for block in blocks:
            # Only process text blocks
            if 'lines' not in block:
                continue

            for line in block['lines']:
                for span in line['spans']:
                    top = span['bbox'][1]
                    bottom = span['bbox'][3]
                    text = span['text']
                    font_size = span['size']

                    # Exclude blocks that are likely headers based on font size, position, and length
                    if (font_size > font_size_threshold and top < header_y_threshold) or len(text.strip()) < min_paragraph_length:
                        continue

                    if previous_bottom is not None and (top - previous_bottom) > spacing_threshold:
                        if len(" ".join(current_paragraph).strip()) >= min_paragraph_length:
                            paragraphs.append(" ".join(current_paragraph).strip())
                        current_paragraph = []

                    current_paragraph.append(text)
                    previous_bottom = bottom

        if current_paragraph and len(" ".join(current_paragraph).strip()) >= min_paragraph_length:
            paragraphs.append(" ".join(current_paragraph).strip())

        return paragraphs

    def populate_sample_data(self):
        # Add 20 sample sessions
        for i in range(1, 11):
            session_id = f"session_{i}"
            self.sessions[session_id] = {
                'title': f"Sample Session {i}",
                'peers': {},
                'current_page': 0,
                'current_paragraph': 0,
            }            

    async def list_sessions(self, websocket):
        #self.populate_sample_data()
        sessions = [
            {'session_id': session_id, 'title': info['title']}
            for session_id, info in self.sessions.items()
        ]

        message = json.dumps({
            'type': 'list_sessions_response',
            'sessions': sessions
        })

        print(f"list_sessions - {sessions}")
        
        await websocket.send(message)            

relay_server = RelayServer()

async def handle_connection(websocket, path): #TODO extract data into variables to pass to functions
    try:
        async for message in websocket:
            #print(f"handle_connection - {message}")
            data = json.loads(message)
            if data["type"] == "register":
                print(f"handle_connection - register {data['device_id']} {data['session_id']}")
                await relay_server.register(websocket, data["device_id"], data["session_id"], data["title"])
            elif data["type"] == "unregister":
                print(f"handle_connection - unregister")
                await relay_server.unregister(websocket)                
            elif data["type"] == "ready":
                print(f"handle_connection - handle_ready {data['device_id']} {data['session_id']} {data['ready']}")
                await relay_server.handle_ready(websocket, data['device_id'], data['session_id'], data['ready'])
            elif data["type"] == "upload_chunk":
                #print(f"handle_connection - upload_chunk {data['device_id']} {data['session_id']} {data['title']} {data['chunk_index']}")
                await relay_server.handle_upload_chunk(websocket, data['device_id'], data['session_id'], data['title'], data['chunk_index'], data['chunk_data'])
            elif data["type"] == "upload_complete":
                #print(f"handle_connection - upload_complete {data['device_id']} {data['session_id']} {data['title']}")
                await relay_server.handle_upload_complete(websocket, data['device_id'], data['session_id'], data['title'])
            elif data["type"] == "list_sessions":
                #print(f"handle_connection - list_sessions")
                await relay_server.list_sessions(websocket)
                
    except websockets.exceptions.ConnectionClosedError:
        pass

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

