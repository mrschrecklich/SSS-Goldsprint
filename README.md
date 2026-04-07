# SSS-Goldsprint

A high-performance, modular, web-based Goldsprint racing simulation designed for events and projectors. This project features a centralized "Source of Truth" architecture to ensure perfect synchronization between race controllers and audience displays.

## 🚀 Tech Stack

- **Backend**: Python 3.12+, FastAPI (Web Server), `websockets`, `uvicorn`, `pydantic-settings`.
- **Frontend**: Vanilla JavaScript (ES6+), CSS3 (Animations & Flexbox), HTML5.
- **Testing**: `pytest` and `pytest-asyncio` for engine and bracket logic.

---

## 🏗️ Architecture Overview

The system is modularized for maintainability and scalability, adhering to senior engineering standards:

### 1. Modular Backend (`src/`)
- **`src/main.py`**: The FastAPI application entry point, managing lifecycle events and WebSocket routing.
- **`src/engine.py`**: The authoritative **Goldsprint Engine**. It handles race states (Countdown, Racing, Finished), physics calculations (speed/distance at 10Hz), and false start detection.
- **`src/bracket.py`**: A robust **Tournament Bracket Manager**. Handles participant registration, category management, and automatic single-elimination bracket generation with "BYE" support and winner propagation.
- **`src/sensor_client.py`**: A dedicated TCP client that ingests raw RPM data from sensors or mocks, providing real-time updates to the engine.
- **`src/websocket_manager.py`**: Decouples communication from logic, managing broadcast groups for all connected Admin and Audience UIs.
- **`src/config.py`**: Centralized configuration using `pydantic-settings`, allowing overrides via environment variables (e.g., `GOLDSPRINT_PORT`).

### 2. Frontend Views (`public/`)
- **Admin View (`admin.html`)**: Optimized for tablets and phones. Features "fat-finger" touch targets, tournament bracket controls, and live race configuration.
- **Audience View (`audience.html`)**: A "10-foot UI" for high-contrast projection. Features dynamic CSS shaking based on real-time RPM and a high-energy start sequence.
- **Launcher (`index.html`)**: Quick access to Admin and Audience views.

### 3. Realistic Mock Sensor (`mock-sensor.py`)
Emulates professional riders with realistic phases:
- **Spin Up**: Rapid acceleration.
- **Maintain**: Holding energy based on configurable fatigue thresholds.
- **Fatigue**: Realistic power drop-off as the rider nears the finish line.

---

## 🛠️ Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone <repo-url>
   cd SSS-Goldsprint
   ```

2. **Install dependencies**:
   It is recommended to use a virtual environment or Conda.
   ```bash
   pip install -r requirements.txt
   ```

---

## 🏃 Running the Project

1. **Start the Web Server**:
   ```bash
   python server.py
   ```
   *The server binds to `0.0.0.0:3000` by default.*

2. **Start the Mock Sensor**:
   ```bash
   python mock-sensor.py
   ```
   *Wait for the `Connected to sensor` message. A 5-second countdown will begin for the simulation.*

3. **Open the Interfaces**:
   - Access `http://localhost:3000` in your browser.
   - Open **Audience View** for the big screen and **Admin View** for the race controller.

---

## ⚙️ Configuration

The system uses `pydantic-settings`. You can configure the server and engine by setting environment variables with the `GOLDSPRINT_` prefix:

- `GOLDSPRINT_PORT`: Server port (default: 3000).
- `GOLDSPRINT_SENSOR_HOST`: Sensor IP (default: 127.0.0.1).
- `GOLDSPRINT_DEFAULT_TARGET_DIST`: Race distance in meters (default: 500).

Rider performance can be adjusted directly in the `mock-sensor.py` configuration block.

---

## 🧪 Testing

The project enforces high code quality through comprehensive testing.

```bash
# Run all tests (Engine, Bracket, and Visual Integrity)
pytest test/
```
