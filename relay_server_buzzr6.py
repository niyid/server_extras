import websockets
import asyncio
import ssl
import json
import geohash2
import random
import uuid
import redis
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from math import radians, sin, cos, sqrt, atan2, ceil
from datetime import datetime, timedelta
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from geopy.distance import geodesic

class IncidentClassifier:
    def __init__(self):
        # Define keywords for each incident category
        self.keyword_mapping = {
            "ACCIDENT": ["accident", "crash"],
            "ROBBERY": ["robbery", "theft"],
            "FLOOD": ["water", "rain"],
            "KIDNAPPING": ["kidnapping", "abduction"],
            "FIRE": ["fire", "blaze", "explosion"],
            "NATURAL DISASTER": ["earthquake", "hurricane", "typhoon", "landslide", "sinkhole"],
            "FIGHT": ["fight", "brawl"],
            "THEFT": ["theft", "burglary"],
            "VANDALISM": ["vandalism", "damage"],
            "ASSAULT": ["assault", "attack"],
            "DEATH": ["murder", "suicide", "killed", "bloodbath"],
            "UNEXPLAINED": ["UFO", "lights", "unknown", "strange"]
        }

    def predict(self, text):
        # Set language to English
        language = "English"
        # Convert text to lowercase for case-insensitive matching
        text_lower = text.lower()
        # Check for keywords in the text and return the corresponding incident label
        for label, keywords in self.keyword_mapping.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return label
        # If no keyword matches found, return "UNKNOWN"
        return "UNKNOWN"
    
    def detect_language(self, text):
        return "English"
        
class RelayServer:
    def __init__(self):
        self.geo_tree = GeoHashTree()
        self.active_connections = {}
        self.redis_conn = redis.StrictRedis(host='localhost', port=6379, db=0)
        self.labels = set(["ACCIDENT", "ROBBERY", "KIDNAPPING", "FIRE", "NATURAL DISASTER", "FIGHT", "THEFT", "VANDALISM", "ASSAULT", "UNEXPLAINED", "DEATH"])
        self.languages = set()
        self.vectorizer = TfidfVectorizer()
        self.incident_classifier = IncidentClassifier()

    async def insert_incident(self, message_data):
        message_id = message_data['message_id']
        print(f"insert_incident {message_id} -> {message_data}")
        self.redis_conn.set(f"message:{message_id}", json.dumps(message_data))

    async def remove_incident(self, message_id):
        await self.redis_conn.delete(f"message:{message_id}")
        
    async def find_similar_incidents(self, geohash, current_time, message_text):
        similar_incidents = []
        radius_km = 10
        time_window_seconds = 30 * 60  # 30 minutes in seconds
        time_window_delta = timedelta(seconds=time_window_seconds)
        # Get messages within the specified radius and time window
        messages_within_radius = self.get_messages_within_radius(geohash, radius_km, current_time - time_window_delta, current_time + time_window_delta)
        
        # Iterate over the messages and filter by similarity
        for message_info in messages_within_radius:
            other_message_text = message_info['message']
            similarity_score = self.calculate_similarity(message_text, other_message_text)
            #print(f"{message_text} ~ {other_message_text} = {similarity_score}")
            if similarity_score > 0.8:  # Adjust the threshold as needed
                message_id = message_info['message_id']
                similar_incidents.append({'message_id': message_id, 'message_text': other_message_text})

        return similar_incidents

    def get_messages_within_radius(self, geohash, radius_km, start_time, end_time):
        messages_within_radius = []
        message_keys = self.redis_conn.keys("message:*")
        
        for message_key in message_keys:
            message_info = json.loads(self.redis_conn.get(message_key) or '{}')

            message_time = datetime.strptime(message_info['incident_time'], '%Y-%m-%d %H:%M:%S')
            message_geohash = message_info['geohash']
            
            if self.geo_tree.calculate_distance(geohash, message_geohash) <= radius_km and start_time <= message_time <= end_time:
                messages_within_radius.append(message_info)

        return messages_within_radius

    def calculate_similarity(self, text1, text2):
        # Fit TF-IDF vectorizer on text1 and transform both text1 and text2
        tfidf_matrix = self.vectorizer.fit_transform([text1, text2])
        # Compute cosine similarity between the transformed vectors
        similarity_score = cosine_similarity(tfidf_matrix)[0, 1]
        return similarity_score
    
    def add_incident_label(self, label, language):
        self.redis_conn.set(f"label:{label}:{language}", 1)

    def get_incident_labels(self, language):
        labels = self.redis_conn.keys(f"label:*:{language}")
        return [label.decode().split(':')[1] for label in labels]

    def get_incident_description(self, text):
        try:
            language = self.incident_classifier.detect_language(text)
            self.languages.add(language)
            label = self.incident_classifier.predict(text)
            return label, language
        except:
            return "UNKNOWN", "UNKNOWN"
        
    async def register(self, websocket, device_id, geohash):
        print(f"Registered device {device_id} at geohash {geohash}")
        user_data = {'device_id': device_id, 'geohash': geohash}
        await self.geo_tree.insert_user(user_data)
        self.active_connections[device_id] = websocket

    async def unregister(self, device_id, geohash):
        print(f"Unregistered device {device_id}")
        await self.geo_tree.remove_user(device_id)

    async def update_location(self, device_id, old_geohash, new_geohash):
        print(f"Updated location for device {device_id} to geohash {new_geohash}")
        await self.unregister(device_id, old_geohash)
        await self.register(self.active_connections[device_id], device_id, new_geohash)

    async def broadcast(self, websocket, device_id, geohash, message, base64_image):
        incident_label, language = self.get_incident_description(message)
        # Add detected incident label dynamically
        # if incident_label not in self.labels:
        #     self.labels.add(incident_label)
        #     self.add_incident_label(incident_label, language)
        
        message_id = str(uuid.uuid4())
        current_time = datetime.fromtimestamp(datetime.now().timestamp())
        expiration_time = current_time + timedelta(days=2)
        
        # Prepend incident label to the message
        message_with_label = f"{incident_label}: {message}"
    
        # Find similar incidents within 10km radius around the same time
        similar_incidents = await self.find_similar_incidents(geohash, current_time, message)
        
        message_data = {
            'action': 'broadcast',
            'message_id': message_id,
            'message': message_with_label,
            'geohash': geohash,
            'expiration_time': expiration_time.strftime('%Y-%m-%d %H:%M:%S'),
            'device_id': device_id,
            'incident_label': incident_label,
            'incident_time': current_time.strftime('%Y-%m-%d %H:%M:%S'), 
            'base64_image': base64_image,
            'similar_incidents': json.dumps(similar_incidents)
        }

        await self.insert_incident(message_data)
        
        #print(f"Broadcast image: {base64_image}")
        
        if message_data:
            print(f"Broadcast sent from device {device_id} at geohash {geohash} - {message_id}")  
            await self.propagate(geohash, message_data, device_id)
        else:
            print(f"Cannot broadcast - invalid message_id {message_id}") 

        # Test similar incidents TODO - comment out later
        # sim_incidents = [
        #     {"id": "0a3f5a3c-6493-4c2d-bb26-d6940a77eef7", "message": "Earthquake reported in downtown area"},
        #     {"id": "1b4e28ba-2fa1-4b78-a63d-2832f7e570af", "message": "Forest fire outbreak in national park"},
        #     {"id": "2c1e42d5-6c3e-47cf-8bc9-8452f6b78ab8", "message": "Tornado warning issued for residential areas"},
        #     {"id": "3e1e5024-0600-48b7-ae7c-3d48d8c1dd63", "message": "Floods causing road closures and property damage"}
        # ]

        # Send echo to sender for testing. TODO - comment out later
        #await websocket.send(json.dumps({"action": "broadcast", "message_id": message_id, "base64_image": base64_image, "similar_incidents": json.dumps(similar_incidents), "message": "TESTECHO-" + message_with_label}))

    async def rebroadcast(self, websocket, device_id, geohash, message_id):
        message_key = f"message:{message_id}"
        message_info = json.loads(self.redis_conn.get(message_key) or '{}')
        data = {key: value for key, value in message_info.items()}
        if message_info:
            print(f"Rebroadcast sent from device {device_id} at geohash {geohash} - {message_id}")  
            await self.propagate(geohash, message_info, device_id)
        else:
            print(f"Cannot rebroadcast - invalid message_id {message_id}") 
            
        # Send echo to sender for testing. TODO - comment out later
        await websocket.send(json.dumps({"action": "rebroadcast", "message_id": message_id, "message": data['message'], "message": data['base64_image']}))                 

    def within_bounds(self, lower, upper, geohash, geohash_2, geo_key):
        target_lat, target_lon = geohash2.decode(geohash_2)
        lat, lon = geohash2.decode(geohash)
        
        # Calculate the distance between the center and the specified location
        distance = geodesic((lat, lon), (target_lat, target_lon)).kilometers
        
        # If the distance is within the radius, add the geohash to users_within_radius
        users_data = []
        if distance <= upper and distance >= lower:
            users_data = json.loads(self.redis_conn.hget(geo_key, 'users') or '[]')

        attenuation = self.geo_tree.calculate_attenuation(lower)
        # Randomly select users in this annulus based on the attenuation
        num_users = int(ceil(attenuation) * len(users_data))
        selected_users = random.sample(users_data, num_users)
        #print(f"within_bounds {lower} - {upper} within {distance} of {len(users_data)} users @ {geohash_2} from {geohash}")

        return selected_users
        

    async def propagate(self, geohash, message_info, source_id):
        if message_info:
            geolocation_keys = self.redis_conn.keys("geohash_tree:*")
            for geo_key in geolocation_keys:
                geohash_2 = geo_key.decode("utf-8").replace("geohash_tree:", "")
                #print(f"Target geohash => {geohash_2}")
                #Remember to exclude all geohashes outside of 200
                for outer_radius in range(20, 200, 20):
                    users = self.within_bounds(outer_radius - 20, outer_radius, geohash, geohash_2, geo_key)
                    if users:
                        #print(f"Bounds {outer_radius - 20} - {outer_radius} has {len(users)} users @ geohash_2")
                        for devid in users:
                            print(f"Sending {message_info['message_id']} to {devid}")
                            await self.send_message(message_info, devid, source_id)

    async def send_message(self, message_info, device_id, source_id):
        if message_info and device_id in self.active_connections and source_id != device_id:
            self.active_connections[device_id]
            message_id = message_info['message_id']
            websocket = self.active_connections.get(device_id)
            if websocket:
                decoded_message_data = {key: value if isinstance(value, bytes) else value for key, value in message_info.items()}
                await websocket.send(json.dumps(decoded_message_data))
                print(f"Sent message with message_id {message_id} to device {device_id}")
            else:
                print(f"Device {device_id} not connected.")
        else:
            print(f"Wrong message or connection not found for device {device_id}.")

    def remove_expired_messages(self):
        current_time = datetime.now()
        expired_message_ids = []
        
        for message_key in self.redis_conn.keys("message:*"):  # Use message keys
            #print(f"message_key={message_key}")
            message_info = json.loads(self.redis_conn.get(message_key) or '{}')
            #print(f"message_info={message_info}")
            try:
                expiration_time = datetime.strptime(message_info['expiration_time'], '%Y-%m-%d %H:%M:%S')
                #print(f"expiration_time={expiration_time}")
                if expiration_time <= current_time:
                    self.redis_conn.delete(message_key)
                    expired_message_ids.append(message_key)
            except KeyError:
                # Handle the case where 'expiration_time' key is missing
                print(f"Expiration time not found for message with id {message_key}. Skipping.")
        if 1 > len(expired_message_ids):
            print(f"Removed {len(expired_message_ids)} expired messages.")
        else:
            print(f"Removed {len(expired_message_ids)} expired message.")

    def classify_incident(self, text):
        try:
            incident_label = self.incident_classifier.predict(text)
            return incident_label
        except Exception as e:
            print(f"An error occurred during incident classification: {str(e)}")
            return "UNKNOWN"                

class GeoHashTree:
    def __init__(self):
        self.redis_conn = redis.StrictRedis(host='localhost', port=6379, db=0)
 
    def calculate_distance(self, geohash_1, geohash_2):
        lat1, lon1 = geohash2.decode(geohash_1)
        lat2, lon2 = geohash2.decode(geohash_2)
        
        return geodesic((lat1, lon1), (lat2, lon2)).kilometers

    async def insert_user(self, user_data):
        geohash = user_data['geohash']
        device_id = user_data['device_id']
        location_key = f"geohash_tree:{geohash}"
        users_set = set(json.loads(self.redis_conn.hget(location_key, 'users') or '[]'))
        users_set.add(device_id)
        user_key = f"user:{device_id}"
        
        self.redis_conn.hset(location_key, 'users', json.dumps(list(users_set)))
        self.redis_conn.set(user_key, json.dumps(user_data))

    async def remove_user(self, device_id):
        user_key = f"user:{device_id}"
        
        user_data = json.loads(self.redis_conn.get(user_key) or '{}')
        geohash = user_data.get('geohash', None)

        geolocation_keys = self.redis_conn.keys("geohash_tree:*")
        for geo_key in geolocation_keys:
            geohash_2 = geo_key.decode("utf-8").replace("geohash_tree:", "")       
            #TODO Remove all occurrences of device_id in all geohash_tree:{geohash} users
            location_key = f"geohash_tree:{geohash_2}"
            users_set = json.loads(self.redis_conn.hget(location_key, 'users') or '[]')
            if device_id in users_set:
                users_set.remove(device_id)
            
            self.redis_conn.hset(location_key, 'users', json.dumps(users_set))
        
        self.redis_conn.delete(user_key)


    def get_users_within_radius(self, geohash, geohash_2, radius):
        users_within_radius = []
        self.traverse_tree(geohash, geohash_2, users_within_radius, radius)
        return users_within_radius

    def get_users_within_annulus(self, geohash, outer_radius, inner_users):
        effective_users = []
        inner_radius = outer_radius - 3
        outer_users = self.get_users_within_radius(geohash, outer_radius)
        ##TODO Should be fetching the location geohashes which contain the users
        # No need to fetch inner_users as they start as empty and outer_users becomes inner_users
        # on next iteration
        #inner_users = self.get_users_within_radius(geohash, inner_radius)
        annulus_users = [user for user in outer_users if user not in inner_users]
        # Calculate attenuation for this annulus based on the propagation distance
        attenuation = self.calculate_attenuation((outer_radius + inner_radius) / 2)
        # Randomly select users in this annulus based on the attenuation
        num_users = int(attenuation * len(annulus_users))
        selected_users = random.sample(annulus_users, num_users)
        effective_users.extend(selected_users)
        return effective_users

    def calculate_attenuation(self, distance):
        max_distance = 200  # Maximum distance in kilometers
        min_attenuation = 0  # Attenuation at max distance
        max_attenuation = 1  # Attenuation at 0 km distance

        # Calculate the attenuation using linear interpolation
        attenuation = max_attenuation - (distance / max_distance) * (max_attenuation - min_attenuation)
        
        return attenuation

    def traverse_tree(self, geohash, geohash_2, users_within_radius, radius):
        node_key = "geohash_tree:" + geohash_2
        # Get the center latitude and longitude of the current geohash
        center_lat, center_lon = geohash2.decode(geohash)
        lat, lon = geohash2.decode(geohash)
        
        # Calculate the distance between the center and the specified location
        distance = geodesic((lat, lon), (center_lat, center_lon)).kilometers
        
        # If the distance is within the radius, add the geohash to users_within_radius
        if distance <= radius:
            users_data = json.loads(self.redis_conn.hget(node_key, 'users') or '[]')
            users_within_radius.append(users_data)

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])    
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        distance = 6371 * c
        return distance
        
relay_server = RelayServer()        

# WebSocket handler
async def handle_connection(websocket, path):
    try:
        async for message in websocket:
            data = {}
            base64_image_start = message.find('"base64_image":')
            base64_image = ''
            if base64_image_start != -1:
                base64_image_start += len('"base64_image":') + 1
                base64_image_end = message.find('"', base64_image_start)  # Find the first occurrence
                base64_image_start = message.find('"', base64_image_start) + 1  # Find the start of the image data
                base64_image_end = message.find('"', base64_image_start)  # Find the second occurrence
                base64_image = message[base64_image_start:base64_image_end]
                message = message[:base64_image_start - 1] + message[base64_image_end + 1:]
                base64_image_index = message.find('"base64_image":')
                if base64_image_index != -1:
                    message = message[:base64_image_index] + '"base64_image": ""}'
            try:
                data = json.loads(message)
            except json.JSONDecodeError as e:
                print("Error decoding JSON:", e)
                continue
            if data["action"] == "register":
                print(f"handle_connection - register {data['device_id']} {data['geohash']}")
                await relay_server.register(websocket, data["device_id"], data["geohash"])
            elif data["action"] == "broadcast":
                print(f"handle_connection - broadcast {data['device_id']} {data['geohash']}")
                await relay_server.broadcast(websocket, data["device_id"], data["geohash"], data["message"], base64_image)
            elif data["action"] == "rebroadcast":
                print(f"handle_connection - rebroadcast {data['device_id']} {data['geohash']}")
                await relay_server.rebroadcast(websocket, data["device_id"], data["geohash"], data["message_id"])
            elif data["action"] == "update_location":
                print(f"handle_connection - update_location {data['device_id']} {data['old_geohash']}=>{data['new_geohash']}")
                await relay_server.update_location(data["device_id"], data["old_geohash"], data["new_geohash"])
    except websockets.exceptions.ConnectionClosedError:
        pass

# Start WebSocket server
async def main():
    key_file_path = "/home/niyid/workspace/buzzr.key"
    crt_file_path = "/home/niyid/workspace/buzzr.crt"

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
    
    async with websockets.serve(handle_connection, "0.0.0.0", 7071, ssl=ssl_context):
            print(f"Server running on port 7071")
            while True:
                # Run remove_expired_messages() every 2 days
                relay_server.remove_expired_messages()
                await asyncio.sleep(2 * 24 * 3600)

asyncio.run(main())
