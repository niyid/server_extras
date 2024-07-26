import express
import https
import fs
import socketio

# Define the port your server will listen on
port = 3001  # Replace with your desired port

# Define paths to your private key and certificate files
private_key_path = '/home/niyid/git/Docs/6degrees.key'  # Replace with the path to your private key
certificate_path = '/home/niyid/git/Docs/6degrees.crt'  # Replace with the path to your certificate

# Read the private key and certificate files
private_key = fs.read_file_sync(private_key_path, 'utf-8')
certificate = fs.read_file_sync(certificate_path, 'utf-8')
credentials = {'key': private_key, 'cert': certificate}

# Create an Express app
app = express()

# Create an HTTPS server using your credentials
server = https.createServer(credentials, app)

# Create a Socket.IO instance attached to the server
io = socketio.Server()

# Store connected clients (peers)
connected_clients = {}

# WebSocket connection handling
@io.event
def connect(socket):
    print(f"New client connected: {socket}")

    @socket.on('receive_command')
    def receive_command(data):
        # Handle the received command data
        device_id = data.get('deviceId')
        origin_device_id = data.get('originDeviceId')
        command = data.get('command')
        receivers = data.get('receivers')
        specific = data.get('specific')
        comment = data.get('comment')
        current_search_depth = data.get('currentSearchDepth')
        search_path_map = data.get('searchPathMap')
        MAX_DEPTH = data.get('MAX_DEPTH')
        cellphone = data.get('cellphone')
        geozone = data.get('geozone')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        employment_search_ids = data.get('employmentSearchIds')
        employment_match_ids = data.get('employmentMatchIds')
        hops = data.get('hops')
        rating = data.get('rating')
        matched_devices = data.get('matchedDevices')
        listing_category_id = data.get('listingCategoryId')
        query = data.get('query')
        listings = data.get('listings')
        resume = data.get('resume')
        swap = data.get('swap')

        # Your handling logic goes here
        pass

    @socket.event
    def disconnect():
        device_id = next((key for key, value in connected_clients.items() if value == socket), None)
        if device_id:
            del connected_clients[device_id]
            print(f"Client disconnected: {device_id}")

# Define a function for logging with timestamp
def log_with_timestamp(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

# Define a function to handle message command
def handle_message_command(
    deviceId, originDeviceId, command, receivers, specific, comment, currentSearchDepth,
    searchPathMap, MAX_DEPTH, cellphone, geozone, latitude, longitude, employmentSearchIds,
    employmentMatchIds, hops, rating, matchedDevices, listingCategoryId, query, listings, resume, swap
):
    if not isinstance(receivers, list) or len(receivers) == 0:
        log_with_timestamp('Empty receivers list.')
        return

    log_with_timestamp(f'Receiver count: {len(receivers)}')
    for receiver in receivers:
        if connected_clients.get(receiver) and receiver != deviceId:
            data = {
                'deviceId': deviceId,
                **({'originDeviceId': originDeviceId} if originDeviceId is not None else {}),
                **({'command': command} if command is not None else {}),
                **({'specific': specific} if specific is not None else {}),
                **({'comment': comment} if comment is not None else {}),
                **({'currentSearchDepth': currentSearchDepth} if currentSearchDepth is not None else {}),
                **({'searchPathMap': searchPathMap} if searchPathMap is not None else {}),
                **({'MAX_DEPTH': MAX_DEPTH} if MAX_DEPTH is not None else {}),
                **({'cellphone': cellphone} if cellphone is not None else {}),
                **({'geozone': geozone} if geozone is not None else {}),
                **({'latitude': latitude} if latitude is not None else {}),
                **({'longitude': longitude} if longitude is not None else {}),
                **({'employmentSearchIds': employmentSearchIds} if employmentSearchIds is not None else {}),
                **({'employmentMatchIds': employmentMatchIds} if employmentMatchIds is not None else {}),
                **({'hops': hops} if hops is not None else {}),
                **({'rating': rating} if rating is not None else {}),
                **({'matchedDevices': matchedDevices} if matchedDevices is not None else {}),
                **({'listingCategoryId': listingCategoryId} if listingCategoryId is not None else {}),
                **({'query': query} if query is not None else {}),
                **({'listings': listings} if listings is not None else {}),
                **({'resume': resume} if resume is not None else {}),
                **({'swap': swap} if swap is not None else {}),
            }

            # Add your handling logic here

            # For example:
            # if specific == 'SEARCH':
            #     data['currentSearchDepth'] += 1
            #     data['searchPathMap'][data['currentSearchDepth']] = str(receiver)
            #     log_with_timestamp(f"PATH => {data['searchPathMap']}")
            #     for key in list(data['searchPathMap'].keys()):
            #         if key > data['currentSearchDepth']:
            #             del data['searchPathMap'][key]
            #     data['rating'] = float(rating)
            #     log_with_timestamp(f"PATH-SHRINK => {data['searchPathMap']}")
            #     log_with_timestamp(f"Depth: {data['currentSearchDepth']} Path: {json.dumps(data['searchPathMap'])}")
            #     io.to(connected_clients[receiver]).emit('receive_command', {'deviceId': deviceId, 'data': data})

# Haversine formula to calculate distance between two points
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth's radius in kilometers
    dLat = deg_to_rad(lat2 - lat1)
    dLon = deg_to_rad(lon2 - lon1)
    a = math.sin(dLat / 2) * math.sin(dLat / 2) + math.cos(deg_to_rad(lat1)) * math.cos(deg_to_rad(lat2)) * \
        math.sin(dLon / 2) * math.sin(dLon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c  # Distance in kilometers

# Convert degrees to radians
def deg_to_rad(deg):
    return deg * (math.pi / 180)


# Define an Express route
@app.route('/')
def index():
    return 'Hello, this is the root path!'

# Start the server
if __name__ == '__main__':
    server.listen(port)
    print(f"Server listening on port {port}")
