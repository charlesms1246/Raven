import os
import time
import base64
import json
import cv2
import requests
import numpy as np

from datetime import datetime
from flask import Flask, Response, jsonify
from ultralytics import YOLO
from PIL import Image
from io import BytesIO

# ------------------ Config ------------------

app = Flask(__name__)

# YOLO model for detection
model = YOLO("models/accident_best.pt")
CONFIDENCE_THRESHOLD = 0.60

# Alert logic parameters
ALERT_COOLDOWN = 20  # seconds
last_alert_time = time.time() - ALERT_COOLDOWN
VERIFICATION_FRAMES = 3
verification_counter = 0
alert_sent = False

# Alert and Stream configuration (main server)
MAIN_SERVER_URL = "http://10.236.79.249:5000/alert"
CAMERA_ID = "primary"
CAMERA_LOCATION = "Nungambakkam"
POLICE_STATION = "City Police Station"
CAMERA_STREAM_URL = "http://10.236.79.113:5003/video_feed"

# Local storage for alerts
LOCAL_STORAGE_DIR = "local_evidence"
os.makedirs(LOCAL_STORAGE_DIR, exist_ok=True)
print(f"✅ Local evidence directory: {LOCAL_STORAGE_DIR}")

# ------------------ Helper Functions ------------------

def notify_main_server_feed_status():
    """
    Notify the main server that the camera is online and the video stream is active.
    """
    try:
        payload = {
            "camera_id": CAMERA_ID,
            "url": CAMERA_STREAM_URL,
            "object": "none"
        }
        resp = requests.post(
            MAIN_SERVER_URL.replace("/alert", "/update_feed"),
            json=payload,
            timeout=15
        )
        if resp.status_code == 200:
            print(f"✅ Camera feed registered with main server.")
        else:
            print(f"❌ Failed to register feed: {resp.status_code}")
    except requests.RequestException as e:
        print(f"⚠️ Error updating feed status: {e}")

def save_alert_locally(frame, metadata):
    """
    Saves image and metadata locally in a structured folder.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    alert_id = f"alert_{CAMERA_ID}_{timestamp}"
    folder = os.path.join(LOCAL_STORAGE_DIR, alert_id)
    os.makedirs(folder, exist_ok=True)

    # Save image
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb)
    image_path = os.path.join(folder, "evidence.png")
    pil_img.save(image_path, format='PNG', optimize=True, quality=95)

    metadata = metadata.copy()
    metadata.pop("image", None)
    metadata["image_path"] = image_path
    metadata["alert_id"] = alert_id

    metadata_path = os.path.join(folder, "metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"✅ Saved alert data locally: {alert_id}")
    return {
        "alert_id": alert_id,
        "image_path": image_path,
        "metadata_path": metadata_path,
        "folder": folder
    }

def calculate_threat_level(confidence, size_ratio, center_proximity):
    """
    Returns a threat level (0–100) based on weighted detection factors.
    """
    w_conf, w_size, w_center = 0.5, 0.3, 0.2
    threat = (confidence * 100 * w_conf +
              size_ratio * 100 * w_size +
              center_proximity * 100 * w_center)
    return min(100, max(0, threat))

def analyze_threat(detected_object, confidence, threat, size_ratio, center_prox):
    """
    Returns hardcoded summary, reasoning, and recommendation based on threat level.
    """
    obj = detected_object.capitalize()
    loc = CAMERA_LOCATION
    c_pct = f"{confidence:.0%}"

    if threat > 70:
        return {
            "summary": f"HIGH RISK: {obj} detected with {c_pct} confidence at {loc}. Immediate action required.",
            "reasoning": ("High-confidence detection and central placement indicate accident. "
                            "Crows is visible and there is increase in traffic."),
            "recommendation": ("Dispatch emergency response immediately. Divert civilians.")
        }
    elif threat > 40:
        return {
            "summary": f"MEDIUM RISK: Potential {obj} detected with {c_pct} confidence at {loc}. Ambulance dispatch advised.",
            "reasoning": ("Moderate confidence and visibility. Victim is not in critical state ."),
            "recommendation": ("Recommend ambulance dispatch. Monitor situation closely.")
        }
    else:
        return {
            "summary": f"LOW RISK: Possible {obj} detected with {c_pct} confidence at {loc}. Monitoring recommended.",
            "reasoning": ("Lower confidence and peripheral placement. Likely false positive or minimal threat."),
            "recommendation": ("Continue observation; no immediate action required unless crowd escalates.")
        }

def send_alert(frame, detected_object, confidence, threat, size_ratio, center_prox):
    """
    Constructs payload and sends alert to main server, also saves locally.
    """
    _, buf = cv2.imencode(".jpg", frame)
    img_b64 = base64.b64encode(buf).decode("utf-8")

    meta = {
        "camera_id": CAMERA_ID,
        "location": CAMERA_LOCATION,
        "police_station": POLICE_STATION,
        "object_detected": detected_object,
        "confidence": float(confidence),
        "threat_level": int(threat),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M:%S"),
        "image": img_b64,
        "url": CAMERA_STREAM_URL,
        **analyze_threat(detected_object, confidence, threat, size_ratio, center_prox),
        "object_size_ratio": float(size_ratio),
        "center_proximity": float(center_prox)
    }

    local = save_alert_locally(frame, meta)
    if local:
        meta["alert_id"] = local["alert_id"]
        meta["evidence_path"] = local["image_path"]
        meta["metadata_path"] = local["metadata_path"]
        meta["local_folder"] = local["folder"]

    try:
        resp = requests.post(MAIN_SERVER_URL, json=meta, timeout=15)
        if resp.status_code == 200:
            print(f"🚨 Alert sent successfully (Threat: {threat:.1f}) -> {meta['summary']}")
        else:
            print(f"❌ Alert failed with status: {resp.status_code}")
    except requests.RequestException as e:
        print(f"⚠️ Error sending alert: {e}")

# ------------------ Frame Generator and Routing ------------------

def generate_frames():
    global last_alert_time, verification_counter, alert_sent

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Error: Unable to open camera.")
        return

    print("✅ Camera initialized.")
    notify_main_server_feed_status()

    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Error capturing frame.")
            break

        try:
            results = model(frame, conf=CONFIDENCE_THRESHOLD)
            now = time.time()
            accident_detected = False
            max_conf = 0.0
            best_box = None

            for res in results:
                for bbox in getattr(res, "boxes", []):
                    conf = float(bbox.conf[0])
                    cls = int(bbox.cls[0])
                    name = model.names[cls]
                    box_coords = bbox.xyxy[0].tolist()

                    color = (0, 0, 255) if name.lower() == "accident" else (0, 255, 0)
                    cv2.rectangle(frame,
                                  (int(box_coords[0]), int(box_coords[1])),
                                  (int(box_coords[2]), int(box_coords[3])),
                                  color, 2)

                    label = f"{name} ({conf:.2f})"
                    cv2.putText(frame,
                                label,
                                (int(box_coords[0]), int(box_coords[1]) - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                    if name.lower() == "accident" and conf > max_conf:
                        accident_detected, max_conf, best_box = True, conf, box_coords

            if accident_detected:
                h, w = frame.shape[:2]
                bw = best_box[2] - best_box[0]
                bh = best_box[3] - best_box[1]
                size_ratio = (bw * bh) / (w * h)

                cx = (best_box[0] + best_box[2]) / 2
                cy = (best_box[1] + best_box[3]) / 2
                fx, fy = w / 2, h / 2

                dist = np.sqrt(((cx - fx) / w) ** 2 + ((cy - fy) / h) ** 2)
                center_prox = 1 - min(dist, 1)

                threat = calculate_threat_level(max_conf, size_ratio, center_prox)

                if now - last_alert_time >= ALERT_COOLDOWN:
                    verification_counter += 1
                    if verification_counter >= VERIFICATION_FRAMES and not alert_sent:
                        send_alert(frame, "accident", max_conf, threat, size_ratio, center_prox)
                        last_alert_time, alert_sent, verification_counter = now, True, 0
                else:
                    verification_counter = 0
            else:
                verification_counter = 0
                alert_sent = False

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cv2.putText(frame, f"Camera: {CAMERA_ID} | {timestamp}",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(frame, f"Location: {CAMERA_LOCATION}",
                        (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            _, buf = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')

        except Exception as e:
            print(f"❌ Frame processing error: {e}")

    cap.release()

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/status')
def status():
    return jsonify({
        "status": "active",
        "camera_id": CAMERA_ID,
        "location": CAMERA_LOCATION,
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("🚀 Camera detection service starting...")
    app.run(host='0.0.0.0', port=5003, debug=False, threaded=True)