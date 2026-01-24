import pygame
import sys
import requests
import time
import threading
import json
import paho.mqtt.client as mqtt

# --- IMPORT VISUALS ---
import sensor_visuals 
# ----------------------

# --- CONFIGURATION ---
SERVER_URL = "http://127.0.0.1:8000" # Still used for Registration
MQTT_BROKER = "test.mosquitto.org"
TOPIC_BASE = "startparking/project"

SCREEN_WIDTH, SCREEN_HEIGHT = 1100, 600
BG_COLOR = (200, 200, 200)
ROAD_COLOR = (60, 60, 60)
WHITE, BLACK, YELLOW, GREEN, RED = (255,255,255), (0,0,0), (255,255,0), (0,200,0), (180,0,0)
MOVING_CAR_COLOR = (220, 30, 30)

CAR_WIDTH = 70
CAR_HEIGHT = 110
CAR_SIZE = (CAR_WIDTH, CAR_HEIGHT)
CAR_SPEED = 5

SPOTS_CONFIG = [
    {'id': 'A1', 'pos': (350, 100), 'status': 'FREE'},
    {'id': 'A2', 'pos': (450, 100), 'status': 'OCCUPIED'},
    {'id': 'A3', 'pos': (550, 100), 'status': 'FREE'},
    {'id': 'A4', 'pos': (650, 100), 'status': 'OCCUPIED'},
    {'id': 'A5', 'pos': (750, 100), 'status': 'FREE'},
    {'id': 'B1', 'pos': (350, 400), 'status': 'FREE'},
    {'id': 'B2', 'pos': (450, 400), 'status': 'OCCUPIED'},
    {'id': 'B3', 'pos': (550, 400), 'status': 'FREE'},
    {'id': 'B4', 'pos': (650, 400), 'status': 'OCCUPIED'},
    {'id': 'B5', 'pos': (750, 400), 'status': 'FREE'},
]

# --- GLOBAL STATE ---
gate_open = False
car_state = "APPROACHING" 
log_messages = ["> System Boot (MQTT Mode)..."]
simulation_car_x, simulation_car_y, simulation_car_angle = -150, 245, -90
target_spot = None 

# --- MQTT CLIENT SETUP ---
mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    add_log("MQTT Connected!")
    # Listen for commands from server
    client.subscribe(f"{TOPIC_BASE}/gate/command")

def on_message(client, userdata, msg):
    global gate_open, car_state, target_spot
    try:
        payload = json.loads(msg.payload.decode())
        action = payload.get("action")
        add_log(f"CMD Received: {action}")
        
        if action == "OPEN_GATE":
            # Logic: Server said open, let's find a spot
            target_spot = next((s for s in SPOTS_CONFIG if s['status'] == 'FREE'), None)
            if target_spot:
                time.sleep(0.5)
                gate_open = True
                add_log(f"Assigned to {target_spot['id']}")
                car_state = "ENTERING"
            else:
                # Safety fallback
                car_state = "LEAVING_FULL"
        
        elif action == "CLOSE_GATE":
            add_log("Gate Denied: FULL")
            car_state = "LEAVING_FULL"
            
    except Exception as e:
        print(e)

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, 1883, 60)
mqtt_client.loop_start()

# --- HELPER FUNCTIONS ---
def send_mqtt_data(device_id, value):
    topic = f"{TOPIC_BASE}/{device_id}/data"
    payload = json.dumps({"device_id": device_id, "value": value})
    mqtt_client.publish(topic, payload)

def initialize_sensors():
    add_log("--- Init Sensors ---")
    try:
        # 1. Register via HTTP (Standard Practice)
        requests.post(f"{SERVER_URL}/register", json={"id": "Entry_Sensor", "type": "sensor", "location": "Gate"})
        for spot in SPOTS_CONFIG:
            requests.post(f"{SERVER_URL}/register", json={"id": spot['id'], "type": "spot", "location": "Zone_A"})
            # 2. Send initial status via MQTT
            send_mqtt_data(spot['id'], spot['status'])
            time.sleep(0.02)
        add_log("--- Ready ---")
    except:
        add_log("Warning: HTTP API Offline")

def check_parking_access():
    add_log("Sensor: CAR_DETECTED")
    # Send via MQTT
    send_mqtt_data("Entry_Sensor", "CAR_DETECTED")

def update_spot_status(spot_id, status):
    send_mqtt_data(spot_id, status)

def add_log(msg):
    log_messages.append(f"> {msg}")
    if len(log_messages) > 15: log_messages.pop(0)

def spawn_next_car():
    global simulation_car_x, simulation_car_y, simulation_car_angle, car_state, gate_open, target_spot
    time.sleep(1.5)
    simulation_car_x, simulation_car_y, simulation_car_angle = -150, 245, -90
    gate_open = False
    target_spot = None
    car_state = "APPROACHING"
    add_log("--- Next Car ---")

# --- PYGAME SETUP ---
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Smart Parking (MQTT Enabled)")
clock = pygame.time.Clock()

# Fonts
font_log = pygame.font.SysFont("Arial", 20)
font_label = pygame.font.SysFont("Arial", 28)
font_display = pygame.font.SysFont("Arial", 40)

threading.Thread(target=initialize_sensors, daemon=True).start()

# --- DRAWING HELPERS ---
def draw_car(surface, x, y, color, angle=0):
    w, h = CAR_SIZE
    car_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    r,g,b = color
    # Shadow
    pygame.draw.rect(car_surf, (0,0,0,50), (4, 4, w-8, h), border_radius=15)
    # Tires
    tire_c = (20,20,20)
    pygame.draw.rect(car_surf, tire_c, (0, 12, 9, 20), border_radius=4) 
    pygame.draw.rect(car_surf, tire_c, (w-9, 12, 9, 20), border_radius=4)
    pygame.draw.rect(car_surf, tire_c, (0, h-32, 9, 20), border_radius=4) 
    pygame.draw.rect(car_surf, tire_c, (w-9, h-32, 9, 20), border_radius=4)
    # Body
    pygame.draw.rect(car_surf, color, (4, 0, w-8, h), border_radius=15)
    # Roof
    roof_c = (max(0,r-40),max(0,g-40),max(0,b-40))
    pygame.draw.rect(car_surf, roof_c, (10, 25, w-20, h-45), border_radius=8)
    # Windows
    win_c = (50,70,90)
    pygame.draw.rect(car_surf, win_c, (12, 28, w-24, 12), border_radius=4) 
    pygame.draw.rect(car_surf, win_c, (12, h-28, w-24, 10), border_radius=4) 
    # Lights
    pygame.draw.ellipse(car_surf, (255,255,200), (8, 2, 10, 6))
    pygame.draw.ellipse(car_surf, (255,255,200), (w-18, 2, 10, 6))
    pygame.draw.ellipse(car_surf, (200,0,0), (8, h-8, 10, 6))
    pygame.draw.ellipse(car_surf, (200,0,0), (w-18, h-8, 10, 6))
    
    rotated = pygame.transform.rotate(car_surf, angle)
    rect = rotated.get_rect(center=(x + w//2, y + h//2))
    surface.blit(rotated, rect.topleft)

def draw_scene():
    screen.fill(BG_COLOR)
    # Road
    pygame.draw.rect(screen, ROAD_COLOR, (0, 250, 900, 100))
    pygame.draw.rect(screen, ROAD_COLOR, (0, 0, 150, SCREEN_HEIGHT))
    
    # Gate Display
    free_count = sum(1 for s in SPOTS_CONFIG if s['status'] == 'FREE')
    pygame.draw.rect(screen, (50,50,50), (220, 150, 10, 100))
    display_rect = pygame.Rect(130, 100, 180, 60)
    pygame.draw.rect(screen, BLACK, display_rect, border_radius=8)
    pygame.draw.rect(screen, (100,100,100), display_rect, 3, border_radius=8)
    
    if free_count > 0:
        text_surf = font_display.render(f"FREE: {free_count}", True, GREEN)
    else:
        text_surf = font_display.render("FULL", True, RED)
    screen.blit(text_surf, text_surf.get_rect(center=display_rect.center))

    # Sensor Loop
    pygame.draw.rect(screen, YELLOW, (180, 250, 80, 100), 3)
    
    # Gate Arm
    pygame.draw.rect(screen, (50, 50, 50), (260, 230, 15, 140)) 
    if gate_open: pygame.draw.rect(screen, GREEN, (260, 235, 80, 12), border_radius=5) 
    else: pygame.draw.rect(screen, RED, (265, 290, 12, 80), border_radius=5) 

    # Spots & Captors
    for spot in SPOTS_CONFIG:
        x, y = spot['pos']
        color = GREEN if spot['status'] == 'FREE' else RED
        pygame.draw.rect(screen, color, (x, y, 80, 120), 3, border_radius=5)
        text = font_label.render(spot['id'], True, BLACK)
        screen.blit(text, (x + 25, y + 50))
        
        # Visual Captor
        sensor_visuals.draw_captor_box(screen, x, y, 80, spot['status'])

        if spot['status'] == 'OCCUPIED':
            draw_car(screen, x+5, y+5, RED)

    # Active Car
    if car_state != "DONE":
        draw_car(screen, simulation_car_x, simulation_car_y, MOVING_CAR_COLOR, angle=simulation_car_angle)

    # Logs
    pygame.draw.rect(screen, (230, 230, 230), (900, 0, 200, SCREEN_HEIGHT))
    for i, msg in enumerate(log_messages):
        screen.blit(font_log.render(msg, True, BLACK), (910, 20 + i * 25))

# --- MAIN LOOP ---
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False

    # Logic
    if car_state == "APPROACHING":
        simulation_car_x += CAR_SPEED
        if simulation_car_x >= 110:
            car_state = "WAITING"
            threading.Thread(target=check_parking_access, daemon=True).start()

    elif car_state == "ENTERING":
        simulation_car_x += CAR_SPEED
        target_x = target_spot['pos'][0] + 5 
        if simulation_car_x >= target_x: simulation_car_x = target_x; car_state = "TURNING"

    elif car_state == "TURNING":
        target_y = target_spot['pos'][1]
        if target_y < 250: # Top Row
            if simulation_car_angle < 0: simulation_car_angle += 5
            else: simulation_car_angle = 0; car_state = "PARKING_MOVE"
        else: # Bottom Row
            if simulation_car_angle > -180: simulation_car_angle -= 5
            else: simulation_car_angle = -180; car_state = "PARKING_MOVE"

    elif car_state == "PARKING_MOVE":
        target_y = target_spot['pos'][1] + 5
        if simulation_car_angle == 0: # Up
            simulation_car_y -= CAR_SPEED
            if simulation_car_y <= target_y: simulation_car_y = target_y; car_state = "PARKED"
        else: # Down
            simulation_car_y += CAR_SPEED
            if simulation_car_y >= target_y: simulation_car_y = target_y; car_state = "PARKED"

    elif car_state == "PARKED":
        target_spot['status'] = 'OCCUPIED'
        add_log(f"Parked in {target_spot['id']}")
        update_spot_status(target_spot['id'], 'OCCUPIED')
        car_state = "DONE"
        threading.Thread(target=spawn_next_car, daemon=True).start()

    elif car_state == "LEAVING_FULL":
        simulation_car_angle += 5
        if simulation_car_angle >= 90: simulation_car_angle = 90; car_state = "LEAVING_DRIVE"
            
    elif car_state == "LEAVING_DRIVE":
        simulation_car_x -= CAR_SPEED 
        if simulation_car_x < -150:
            car_state = "DONE"
            threading.Thread(target=spawn_next_car, daemon=True).start()

    draw_scene()
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()