const express = require('express');
const https = require('https');
const fs = require('fs');
const socketIO = require('socket.io');

// Define the port your server will listen on
const port = 3001; // Replace with your desired port

// Define paths to your private key and certificate files
const privateKeyPath = '/home/niyid/git/Docs/6degrees.key'; // Replace with the path to your private key
const certificatePath = '/home/niyid/git/Docs/6degrees.crt'; // Replace with the path to your certificate

// Read the private key and certificate files
const privateKey = fs.readFileSync(privateKeyPath, 'utf8');
const certificate = fs.readFileSync(certificatePath, 'utf8');
const credentials = { key: privateKey, cert: certificate };

// Create an Express app
const app = express();

// Create an HTTPS server using your credentials
const server = https.createServer(credentials, app);

// Create a Socket.IO instance attached to the server
const io = socketIO(server);

// Store connected clients (peers)
const connectedClients = {};

// WebSocket connection handling
io.on('connection', (socket) => {
  // Handle new client connections
  socket.on('receive_command', (data) => {
    const { deviceId, originDeviceId, command, receivers, specific, comment, currentSearchDepth, searchPathMap, MAX_DEPTH, cellphone, geozone, latitude, longitude, employmentSearchIds, employmentMatchIds, hops, rating, matchedDevices, listingCategoryId, query, listings, resume, swap } = data;
    let logMessage = '';

    if (deviceId !== undefined) {
      logMessage += `deviceId: ${deviceId}\n`;
    }
		if (originDeviceId !== undefined) {
			logMessage += `originDeviceId: ${originDeviceId}\n`;
		}
		if (command !== undefined) {
			logMessage += `command: ${command}\n`;
		}
		if (specific !== undefined) {
			logMessage += `specific: ${specific}\n`;
		}
		if (comment !== undefined) {
			logMessage += `comment: ${comment}\n`;
		}
		if (searchPathMap !== undefined) {
			logMessage += `searchPathMap: ${JSON.stringify(searchPathMap)}\n`;
		}
		if (MAX_DEPTH !== undefined) {
			logMessage += `MAX_DEPTH: ${MAX_DEPTH}\n`;
		}
		if (cellphone !== undefined) {
			logMessage += `cellphone: ${cellphone}\n`;
		}
		if (geozone !== undefined) {
			logMessage += `geozone: ${geozone}\n`;
		}
		if (latitude !== undefined) {
			logMessage += `latitude: ${latitude}\n`;
		}
		if (longitude !== undefined) {
			logMessage += `longitude: ${longitude}\n`;
		}
		if (employmentSearchIds !== undefined) {
			logMessage += `employmentSearchIds: ${employmentSearchIds}\n`;
		}
		if (employmentMatchIds !== undefined) {
			logMessage += `employmentMatchIds: ${employmentMatchIds}\n`;
		}
		if (hops !== undefined) {
			logMessage += `hops: ${hops}\n`;
		}
		if (rating !== undefined) {
			logMessage += `rating: ${rating}\n`;
		}
		if (matchedDevices !== undefined) {
			logMessage += `rating: ${matchedDevices}\n`;
		}
		if (listingCategoryId !== undefined) {
			logMessage += `listingCategoryId: ${listingCategoryId}\n`;
		}
		if (query !== undefined) {
			logMessage += `query: ${query}\n`;
		}
		if (listings !== undefined) {
			logMessage += `listings: ${listings}\n`;
		}
		if (resume !== undefined) {
			logMessage += `resume: ${resume}\n`;
		}
		if (swap !== undefined) {
			logMessage += `resume: ${swap}\n`;
		}

		logWithTimestamp(logMessage);

		if(deviceId) {
			connectedClients[deviceId] = socket.id;
		}
    switch (command) {
      case 'message':
        logWithTimestamp(`Handling ${specific} command from: ${deviceId}`);
        handleMessageCommand(deviceId, originDeviceId, command, receivers, specific, comment, currentSearchDepth, searchPathMap, MAX_DEPTH, cellphone, geozone, latitude, longitude, employmentSearchIds, employmentMatchIds, hops, rating, matchedDevices, listingCategoryId, query, listings, resume, swap);
        break;
      default:
        logWithTimestamp(`Unknown command: ${command}`);
    }
  });

  // Handle client disconnection
  socket.on('disconnect', () => {
    const deviceId = Object.keys(connectedClients).find(key => connectedClients[key] === socket.id);
    if (deviceId) {
      delete connectedClients[deviceId];
      logWithTimestamp(`Client disconnected: ${deviceId}`);
    }
  });
});

function logWithTimestamp(message) {
  const timestamp = new Date().toLocaleString();
  console.log(`[${timestamp}] ${message}`);
}

function handleMessageCommand(
  deviceId,
  originDeviceId,
  command,
  receivers,
  specific,
  comment,
  currentSearchDepth,
  searchPathMap,
  MAX_DEPTH,
  cellphone,
  geozone,
  latitude,
  longitude,
  employmentSearchIds,
  employmentMatchIds,
  hops,
  rating,
  matchedDevices,
  listingCategoryId,
  query,
  listings,
  resume,
  swap
) {
  if (!Array.isArray(receivers) || receivers.length === 0) {
    logWithTimestamp('Empty receivers list.');
    return;
  }

	logWithTimestamp(`Receiver count: ${receivers.length}`);
  receivers.forEach((receiver) => {
    if (connectedClients[receiver] && receiver !== deviceId) {
			const data = {
				deviceId: deviceId,
				...(originDeviceId !== undefined ? { originDeviceId } : {}),
				...(command !== undefined ? { command } : {}),
				...(specific !== undefined ? { specific } : {}),
				...(comment !== undefined ? { comment } : {}),
				...(currentSearchDepth !== undefined ? { currentSearchDepth } : {}),
				...(searchPathMap !== undefined ? { searchPathMap } : {}),
				...(MAX_DEPTH !== undefined ? { MAX_DEPTH } : {}),
				...(cellphone !== undefined ? { cellphone } : {}),
				...(geozone !== undefined ? { geozone } : {}),
				...(latitude !== undefined ? { latitude } : {}),
				...(longitude !== undefined ? { longitude } : {}),
				...(employmentSearchIds !== undefined ? { employmentSearchIds } : {}),
				...(employmentMatchIds !== undefined ? { employmentMatchIds } : {}),
				...(hops !== undefined ? { hops } : {}),
				...(rating !== undefined ? { rating } : {}),
				...(matchedDevices !== undefined ? { matchedDevices } : {}),				
				...(listingCategoryId !== undefined ? { listingCategoryId } : {}),				
				...(query !== undefined ? { query } : {}),				
				...(listings !== undefined ? { listings } : {}),				
				...(resume !== undefined ? { resume } : {}),				
				...(swap !== undefined ? { swap } : {}),				
			};
			//logWithTimestamp(`data: ${JSON.stringify(data)}}`);
			
			switch (specific) {
	      case 'SEARCH':
		    	data.currentSearchDepth += 1
		      data.searchPathMap[data.currentSearchDepth] = receiver.toString();
		      logWithTimestamp(`PATH => ${data.searchPathMap}`);	
					for (let key = data.currentSearchDepth + 1; key <= data.searchPathMap.size; key++) {
						 data.searchPathMap.delete(key);
					}
					data.rating = parseFloat(rating) 		    
		      logWithTimestamp(`PATH-SHRINK => ${data.searchPathMap}`);	
  				logWithTimestamp(`Depth: ${data.currentSearchDepth} Path: ${JSON.stringify(data.searchPathMap)}`);
					io.to(connectedClients[receiver]).emit('receive_command', { deviceId, data });
		      break;
	      case 'SEARCH_LISTING':
		    	data.currentSearchDepth += 1
		      data.searchPathMap[data.currentSearchDepth] = receiver.toString();
		      logWithTimestamp(`PATH => ${data.searchPathMap}`);	
					for (let key = data.currentSearchDepth + 1; key <= data.searchPathMap.size; key++) {
						 data.searchPathMap.delete(key);
					}
					data.rating = parseFloat(rating) 		    
		      logWithTimestamp(`PATH-SHRINK => ${data.searchPathMap}`);	
  				logWithTimestamp(`Depth: ${data.currentSearchDepth} Path: ${JSON.stringify(data.searchPathMap)}`);
					io.to(connectedClients[receiver]).emit('receive_command', { deviceId, data });
		      break;
	      case 'CAST_LISTING':
		    	data.currentSearchDepth += 1
		      data.searchPathMap[data.currentSearchDepth] = receiver.toString();
		      logWithTimestamp(`PATH => ${data.searchPathMap}`);	
					for (let key = data.currentSearchDepth + 1; key <= data.searchPathMap.size; key++) {
						 data.searchPathMap.delete(key);
					}
					data.rating = parseFloat(rating) 		    
		      logWithTimestamp(`PATH-SHRINK => ${data.searchPathMap}`);	
  				logWithTimestamp(`Depth: ${data.currentSearchDepth} Path: ${JSON.stringify(data.searchPathMap)}`);
					io.to(connectedClients[receiver]).emit('receive_command', { deviceId, data });
		      break;
	      case 'ATTACH':
	      	//Bidirectional emit; both sender (deviceId) and receiver need to act
				 	logWithTimestamp(`${deviceId} <=> ${receiver}`);
				 	//create copy of data for receiver. set deviceId = receiver
				 	const data2 = {
  									...data
								};
					data2.deviceId = deviceId;
					data.deviceId = receiver;
					io.to(connectedClients[receiver]).emit('receive_command', { data2 });
				  io.to(connectedClients[deviceId]).emit('receive_command', { data });
	      	break;
	      case 'DETACH':
	      	//Unidirectional emit; only receiver needs to act
				 	logWithTimestamp(`${deviceId} => ${receiver}`);
				  io.to(connectedClients[receiver]).emit('receive_command', { deviceId, data });
	      	break;
	      case 'RESULT':
	      	if(originDeviceId) {
						io.to(connectedClients[originDeviceId]).emit('receive_command', { originDeviceId, data });
					 	//logWithTimestamp(`Emitted ${JSON.stringify(data)} => ${originDeviceId}`);				  
	      	}
		    	break;
	      case 'CHAT':		      
				 	logWithTimestamp(`${deviceId} => ${receiver}`);
				  io.to(connectedClients[receiver]).emit('receive_command', { data });
	      	break;
	      case 'RATING':		      
				 	logWithTimestamp(`${deviceId} => ${receiver}`);
				 	data.sender = deviceId
				 	data.rating = parseFloat(rating)
				  io.to(connectedClients[receiver]).emit('receive_command', { data });
	      	break;
		    default:
		      logWithTimestamp(`Unknown specific: ${specific}`);
	    }
    }
  });
}

// Haversine formula to calculate distance between two points
function haversineDistance(lat1, lon1, lat2, lon2) {
  const R = 6371; // Earth's radius in kilometers
  const dLat = degToRad(lat2 - lat1);
  const dLon = degToRad(lon2 - lon1);
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(degToRad(lat1)) * Math.cos(degToRad(lat2)) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c; // Distance in kilometers
}

// Convert degrees to radians
function degToRad(deg) {
  return deg * (Math.PI / 180);
}

app.get('/', (req, res) => {
    res.send('Hello, this is the root path!');
});

server.listen(port, () => {
    logWithTimestamp(`Server listening on port ${port}`);
});


