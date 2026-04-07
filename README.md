# SSS-Goldsprint

A web-based Goldsprint simulation project featuring real-time RPM tracking and visualization.

## Current Status

The project consists of a Node.js backend that serves a frontend and manages real-time data flow via WebSockets. It is designed to ingest data from a sensor source (real or simulated) over a TCP connection.

### Core Components:
- **Web Server (`server.js`)**: 
    - Built with Express.
    - Serves static assets from the `public/` directory.
    - Hosts a WebSocket server for broadcasting player states to connected clients.
    - Connects to a TCP sensor source on `127.0.0.1:5000`.
- **Frontend (`public/`)**:
    - `index.html`: Main interface.
    - `app.js`: Handles WebSocket communication and UI updates.
    - `style.css`: Visual styling for the application.
- **Mock Sensor (`mock-sensor.py`)**:
    - A Python script that simulates RPM data for two players.
    - Acts as a TCP server on port `5000`.

## Getting Started

### 1. Activate the Mock Input
The mock sensor simulates bicycle RPM data and must be running for the web server to receive data.

```bash
python mock-sensor.py
```

### 2. Start the Web Server
Install dependencies first, then start the server.

```bash
# From the SSS-Goldsprint directory
npm install
node server.js
```

### 3. Access the Application
Once both the mock sensor and the web server are running, you can access the interface in your browser:

- **URL**: [http://localhost:3000](http://localhost:3000)

## Technical Details
- **TCP Data Format**: The server expects data in the format `P1:RPM\nP2:RPM\n` (e.g., `P1:120\nP2:115\n`).
- **Update Rate**: The mock sensor currently broadcasts at 10Hz (every 100ms).
