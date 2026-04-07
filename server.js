const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const net = require('net');
const path = require('path');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

// Configuration
const PORT = process.env.PORT || 3000;
const MOCK_SENSOR_HOST = '127.0.0.1';
const MOCK_SENSOR_PORT = 5000;

// Serve static assets from 'public' folder
app.use(express.static(path.join(__dirname, 'public')));

// Simple player state
let players = {
    p1: 0,
    p2: 0
};

// WebSocket logic
wss.on('connection', (ws) => {
    console.log('Client connected to WebSocket server');
    
    // Send initial state
    ws.send(JSON.stringify(players));

    ws.on('close', () => {
        console.log('Client disconnected');
    });
});

// Broadcast state to all WebSocket clients
function broadcastState() {
    const data = JSON.stringify(players);
    wss.clients.forEach((client) => {
        if (client.readyState === WebSocket.OPEN) {
            client.send(data);
        }
    });
}

// Data ingestion from mock sensor (or real hardware via TCP/Serial-to-TCP bridge)
function connectToSensor() {
    const client = new net.Socket();
    
    client.connect(MOCK_SENSOR_PORT, MOCK_SENSOR_HOST, () => {
        console.log(`Connected to sensor data source on ${MOCK_SENSOR_HOST}:${MOCK_SENSOR_PORT}`);
    });

    client.on('data', (data) => {
        const message = data.toString();
        // Parsing "P1:120\nP2:115\n"
        const lines = message.split('\n');
        lines.forEach(line => {
            if (line.startsWith('P1:')) {
                players.p1 = parseInt(line.split(':')[1]) || 0;
            } else if (line.startsWith('P2:')) {
                players.p2 = parseInt(line.split(':')[1]) || 0;
            }
        });
        
        broadcastState();
    });

    client.on('close', () => {
        console.log('Sensor connection closed. Retrying in 2 seconds...');
        setTimeout(connectToSensor, 2000);
    });

    client.on('error', (err) => {
        console.error('Sensor connection error:', err.message);
    });
}

// Start everything
server.listen(PORT, () => {
    console.log(`Web server running on http://localhost:${PORT}`);
    // Start trying to connect to sensor data source
    connectToSensor();
});
