import uvicorn
import json
import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import paho.mqtt.client as mqtt
from pydantic import BaseModel

# --- CONFIGURATION ---
MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT = 1883
TOPIC_BASE = "startparking/project"

app = FastAPI(title="Smart Parking Hybrid Platform")

# --- CORS ---
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# --- DATABASE ---
devices_db = {}
data_store = []
subscriptions = []
notification_queues = {}

# --- MQTT LOGIC (The "Ears" for Sensors) ---
def on_connect(client, userdata, flags, rc):
    print(f"✅ MQTT Connected to {MQTT_BROKER}")
    # Subscribe to data from ANY device
    client.subscribe(f"{TOPIC_BASE}/+/data")

def on_message(client, userdata, msg):
    try:
        # Parse JSON from Sensor
        payload = json.loads(msg.payload.decode())
        device_id = payload.get("device_id")
        value = payload.get("value")
        
        print(f"⚡ MQTT MSG: {device_id} -> {value}")
        
        # 1. Archive Data
        data_store.append(payload)
        
        # 2. Update Status in DB
        if device_id in devices_db:
            devices_db[device_id]['current_status'] = value

        # 3. LOGIC: If a car is at the gate, decide immediately
        if device_id == "Entry_Sensor" and value == "CAR_DETECTED":
            evaluate_gate_access()
            
    except Exception as e:
        print(f"Error processing MQTT: {e}")

def evaluate_gate_access():
    # Count occupied spots
    occupied = sum(1 for d in devices_db.values() if d.get('current_status') == 'OCCUPIED')
    total = 10
    print(f"📊 Logic Check: {occupied}/{total} Occupied")
    
    # Decide
    if occupied >= total:
        action = "CLOSE_GATE"
        trigger_notification("PARKING_FULL", "URGENT: Parking is Full!")
    else:
        action = "OPEN_GATE"
    
    # Send Command back via MQTT
    print(f"📢 Publishing Command: {action}")
    mqtt_client.publish(f"{TOPIC_BASE}/gate/command", json.dumps({"action": action}))

# Start MQTT Client
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

def start_mqtt():
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_forever()

threading.Thread(target=start_mqtt, daemon=True).start()

# --- HTTP ENDPOINTS (For Dashboard & Registration) ---
class Device(BaseModel):
    id: str
    type: str
    location: str

@app.post("/register")
def register(device: Device):
    devices_db[device.id] = device.dict()
    devices_db[device.id]['current_status'] = "FREE"
    return {"status": "registered"}

@app.get("/history")
def get_history():
    return data_store[-15:]

# --- NOTIFICATION SYSTEM ---
class Subscription(BaseModel):
    client_id: str
    event_type: str

@app.post("/subscribe")
def subscribe(sub: Subscription):
    if sub.dict() not in subscriptions:
        subscriptions.append(sub.dict())
    return {"status": "subscribed"}

@app.get("/notifications/{client_id}")
def get_notifications(client_id: str):
    alerts = notification_queues.get(client_id, [])
    notification_queues[client_id] = []
    return alerts

def trigger_notification(event_type, message):
    for sub in subscriptions:
        if sub['event_type'] == event_type:
            c_id = sub['client_id']
            if c_id not in notification_queues: notification_queues[c_id] = []
            notification_queues[c_id].append(message)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)