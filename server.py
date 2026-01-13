from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Smart Parking IoT Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (for testing)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],
)
# --- In-Memory Database (Simple Storage) ---
# this will be a database.
devices_db = {}     # Stores registered devices: {'Spot-A1': {...}}
data_store = []     # Stores history of data: [{'id': 'Spot-A1', 'status': 'OCCUPIED'}]
subscriptions = []  # Stores subscriptions: [{'event': 'FREE', 'callback': 'http://...'}]
command_queue = {}  # Stores commands for devices: {'Gate-01': 'OPEN'}

# --- Data Models (The Shape of your Data) ---
class Device(BaseModel):
    id: str
    type: str # 'sensor' or 'actuator'
    location: str

class DataPayload(BaseModel):
    device_id: str
    value: str # e.g., "OCCUPIED", "FREE", "CAR_DETECTED"

class Command(BaseModel):
    target_id: str
    action: str

# --- 1. Service d’enregistrement (Registration) ---
@app.post("/register")
def register_device(device: Device):
    devices_db[device.id] = device.dict()
    print(f"✅ Device Registered: {device.id} at {device.location}")
    return {"status": "registered", "device": device.id}

@app.get("/devices")
def get_devices():
    return devices_db

# --- 2. Service de consultation de données (Data Ingestion) ---
@app.post("/data")
def receive_data(payload: DataPayload):
    # Save to history
    data_store.append(payload.dict())
    print(f"📡 Data Received from {payload.device_id}: {payload.value}")
    
    # LOGIC: Update the in-memory device status if it's a parking spot
    if payload.device_id.startswith("Spot"):
        if payload.device_id in devices_db:
            # We add a 'status' field to the device record to track it easily
            devices_db[payload.device_id]['current_status'] = payload.value

    # LOGIC: If Entry Sensor detects a car, check if parking is full
    if payload.device_id == "Entry_Sensor" and payload.value == "CAR_DETECTED":
        # Count occupied spots from our "Live DB"
        # We count any device that is type 'parking_spot' and status is 'OCCUPIED'
        occupied_count = 0
        for dev_id, dev_data in devices_db.items():
            if dev_data.get('type') == 'parking_spot' and dev_data.get('current_status') == 'OCCUPIED':
                occupied_count += 1
        
        total_spots = 10 
        print(f"DEBUG: Occupied: {occupied_count} / {total_spots}")

        if occupied_count >= total_spots:
            trigger_event("PARKING_FULL", f"URGENT: Parking is Full at {occupied_count} cars!")
            return {"response": "PARKING_FULL", "action": "CLOSE_GATE"}
        else:
            return {"response": "ACCESS_GRANTED", "action": "OPEN_GATE"}

    return {"status": "data_received"}

# --- 3. Service d’exécution d’actions (Commands) ---
@app.post("/command")
def send_command(cmd: Command):
    # Add command to queue for the device to pick up
    command_queue[cmd.target_id] = cmd.action
    print(f"⚠️ Command Queued for {cmd.target_id}: {cmd.action}")
    return {"status": "command_queued"}

@app.get("/command/{device_id}")
def get_command(device_id: str):
    # Devices poll this endpoint to see if they have work to do
    action = command_queue.get(device_id)
    if action:
        del command_queue[device_id] # Clear command after reading
        return {"action": action}
    return {"action": None}

@app.get("/history")
def get_history():
    # Return the last 10 items from the data store
    return data_store[-10:]

# --- 4. Service de Notification (Pub/Sub) ---
# Store notifications for clients: {'client_1': ['Alert: Full!']}
notification_queues = {} 

class Subscription(BaseModel):
    client_id: str
    event_type: str # e.g., "PARKING_FULL"

@app.post("/subscribe")
def subscribe(sub: Subscription):
    # Register the client's interest
    subscriptions.append(sub.dict())
    # Create an empty mailbox for them if it doesn't exist
    if sub.client_id not in notification_queues:
        notification_queues[sub.client_id] = []
    
    print(f"🔔 Client {sub.client_id} subscribed to {sub.event_type}")
    return {"status": "subscribed"}

@app.get("/notifications/{client_id}")
def get_notifications(client_id: str):
    # Return any waiting messages and clear the queue
    alerts = notification_queues.get(client_id, [])
    notification_queues[client_id] = [] # Clear after reading
    return alerts

# --- Helper to trigger alerts ---
def trigger_event(event_type, message):
    # Check if anyone is subscribed to this event
    for sub in subscriptions:
        if sub['event_type'] == event_type:
            # Add message to their queue
            if sub['client_id'] not in notification_queues:
                notification_queues[sub['client_id']] = []
            notification_queues[sub['client_id']].append(message)
            print(f"⚠️ Notification sent to {sub['client_id']}: {message}")

# --- Run the Server ---
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)