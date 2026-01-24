# 🚗 Smart Parking IoT Platform

A complete IoT Digital Twin for smart parking management, featuring a real-time simulator, a hybrid communication platform (MQTT + HTTP), and a web dashboard.

## 🏗 Architecture
* **Protocol A (Fast):** Sensors communicate via **MQTT** (Mosquitto).
* **Protocol B (Management):** Dashboard communicates via **HTTP/REST**.
* **Simulation:** Developed in Python (Pygame) with realistic physics and hardware visualization.

## 🚀 Installation
1. Install Python 3.x
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
3. Run MQTT Server
   ```bash
   python server_mqtt.py
4. Run Parking Simulation
   ```bash
   python parking_simulator_mqtt.py 
