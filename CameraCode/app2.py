import cv2
import time
import torch
import requests
import base64
import numpy as np
import json
import os
from flask import Flask, Response
from datetime import datetime
from ultralytics import YOLO
from PIL import Image
from io import BytesIO

app = Flask(__name__)

model = YOLO("models/gun.pt")
CONFIDENCE_THRESHOLD = 0.60  

ALERT_COOLDOWN = 20  # Seconds between alerts
last_alert_time = time.time() - ALERT_COOLDOWN  # Initialize to allow immediate first alert
VERIFICATION_FRAMES = 3  
verification_counter = 0 

# Flag to track if we're in alert cooldown period
alert_sent = False

MAIN_SERVER_URL = "http://192.168.0.200:5000/update_feed"
ALERT_SERVER_URL = MAIN_SERVER_URL

CAMERA_ID = "primary"
CAMERA_LOCATION = "Gandhipuram"
POLICE_STATION = "City Police Station"
CAMERA_STREAM_URL = "http://192.168.0.1:5003/video_feed"

# Local storage directory for images
LOCAL_STORAGE_DIR = "local_evidence"

# Create local storage directory if it doesn't exist
if not os.path.exists(LOCAL_STORAGE_DIR):
    os.makedirs(LOCAL_STORAGE_DIR)
    print(f"✅ Created local storage directory: {LOCAL_STORAGE_DIR}")

def notify_main_server():
    """Notifies the main server that the camera feed is active."""
    try:
        data = {
            "camera_id": CAMERA_ID,
            "url": CAMERA_STREAM_URL,
            "object": "gun"
        }
        response = requests.post(MAIN_SERVER_URL, json=data, timeout=15)
        if response.status_code == 200:
            print(f"✅ Camera feed registered: {CAMERA_ID}")
        else:
            print(f"❌ Failed to update main server. Status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error notifying main server: {e}")

def save_alert_locally(frame, metadata):
    """
    Saves alert data locally in a folder structure.
    Creates a unique folder for each alert and stores both the image and metadata JSON.
    
    Args:
        frame: The camera frame with the detection
        metadata: Dict containing all alert metadata
    
    Returns:
        dict: Paths for the stored files
    """
    try:
        # Generate a unique alert ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        alert_id = f"alert_{CAMERA_ID}_{timestamp}"
        
        # Create folder path with alert_id
        folder_path = os.path.join(LOCAL_STORAGE_DIR, alert_id)
        os.makedirs(folder_path, exist_ok=True)
        
        # Convert frame to image and save
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img)
        
        # Create image file path
        image_path = os.path.join(folder_path, "evidence.png")
        pil_img.save(image_path, format='PNG', optimize=True, quality=95)
        
        # Prepare metadata for JSON storage
        # Remove the base64 image data to avoid redundant storage
        metadata_copy = metadata.copy()
        
        # Store the path to the image instead of the base64 data
        if "image" in metadata_copy:
            del metadata_copy["image"]
        
        metadata_copy["image_path"] = image_path
        metadata_copy["alert_id"] = alert_id
        
        # Save metadata as JSON
        metadata_path = os.path.join(folder_path, "metadata.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata_copy, f, indent=2)
        
        print(f"✅ Alert data saved locally: {alert_id}")
        
        return {
            "alert_id": alert_id,
            "image_path": image_path,
            "metadata_path": metadata_path,
            "folder": folder_path
        }
            
    except Exception as e:
        print(f"❌ Local storage error: {str(e)}")
        return None

def calculate_threat_level(confidence, object_size_ratio, center_proximity):
    """
    Calculate a threat level based on multiple factors:
    - Detection confidence
    - Object size relative to frame
    - Proximity to center of frame (more centered = higher threat)
    
    Returns a value between 0-100
    """
    confidence_weight = 0.5
    size_weight = 0.3
    center_weight = 0.2
    
    threat_level = (
        (confidence * 100) * confidence_weight +
        (object_size_ratio * 100) * size_weight +
        (center_proximity * 100) * center_weight
    )
    
    return min(100, max(0, threat_level))

def analyze_threat_with_hardcoded_statements(detected_object, confidence, threat_level, object_size_ratio, center_proximity):
    """
    Analyze the threat and generate summary, reasoning, and recommendations using hardcoded statements.
    
    Args:
        detected_object: The type of object detected (e.g., "gun")
        confidence: Detection confidence (0-1)
        threat_level: Calculated threat level (0-100)
        object_size_ratio: Size of the object relative to frame (0-1)
        center_proximity: How centered the object is in frame (0-1)
        
    Returns:
        dict: Contains summary, reasoning, and recommendation
    """
    try:
        # Hardcoded risk statements based on threat level
        if threat_level > 70:
            # High Risk
            summary = f"HIGH RISK: {detected_object.capitalize()} detected with {confidence:.0%} confidence at {CAMERA_LOCATION}. Immediate action required."
            reasoning = "This detection represents a severe security threat due to high confidence levels and prominent object positioning. The weapon's visibility and central placement in the frame indicate an active threat situation requiring immediate intervention."
            recommendation = "URGENT ACTION REQUIRED: Dispatch emergency response team immediately. Notify all nearby units and establish perimeter. Evacuate civilians from the area if necessary."
            
        elif threat_level > 40:
            # Medium Risk
            summary = f"MEDIUM RISK: Potential {detected_object} detected with {confidence:.0%} confidence at {CAMERA_LOCATION}. Enhanced monitoring advised."
            reasoning = "This detection shows moderate threat indicators with reasonable confidence levels. While not immediately critical, the presence of a potential weapon warrants increased surveillance and preparation for possible escalation."
            recommendation = "MODERATE RESPONSE: Increase patrol presence in the area. Alert nearby officers and maintain heightened surveillance. Prepare response team for potential deployment."
            
        else:
            # Low Risk
            summary = f"LOW RISK: Possible {detected_object} detected with {confidence:.0%} confidence at {CAMERA_LOCATION}. Continued monitoring recommended."
            reasoning = "This detection shows lower confidence levels and may represent a false positive or non-threatening object. The positioning and size suggest minimal immediate risk, but continued observation is warranted."
            recommendation = "LOW PRIORITY: Continue standard monitoring procedures. Log the detection for pattern analysis. No immediate action required unless situation escalates."
        
        print(f"✅ Threat Analysis Complete - Risk Level: {threat_level:.1f}")
        return {
            "summary": summary,
            "reasoning": reasoning,
            "recommendation": recommendation
        }
        
    except Exception as e:
        print(f"❌ Threat Analysis failed: {str(e)}")
        # Fallback to basic analysis
        summary = f"{detected_object.capitalize()} detected with {confidence:.0%} confidence. Threat level: {threat_level:.0f}/100."
        reasoning = f"Detection confidence: {confidence:.2f}, Object size: {object_size_ratio:.2f}, Position: {center_proximity:.2f}"
        recommendation = "Continue monitoring the situation and follow standard protocols."
        
        return {
            "summary": summary,
            "reasoning": reasoning,
            "recommendation": recommendation
        }

def send_alert(frame, detected_object, confidence, threat_level, object_size_ratio=0, center_proximity=0):
    """Sends alert to server with image, metadata, threat assessment, and recommendations."""
    try:
        _, buffer = cv2.imencode('.jpg', frame)
        base64_image = base64.b64encode(buffer).decode('utf-8')
        
        # Use hardcoded statements for analysis
        threat_analysis = analyze_threat_with_hardcoded_statements(
            detected_object, 
            confidence, 
            threat_level, 
            object_size_ratio, 
            center_proximity
        )
        
        summary = threat_analysis["summary"]
        reasoning = threat_analysis["reasoning"]
        recommendation = threat_analysis["recommendation"]

        # Create complete metadata object
        metadata = {
            "camera_id": CAMERA_ID,
            "location": CAMERA_LOCATION,
            "url": CAMERA_STREAM_URL,
            "police_station": POLICE_STATION,
            "object_detected": detected_object,
            "confidence": float(confidence),
            "threat_level": int(threat_level),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M:%S"),
            "image": base64_image,  # Will be removed before local storage
            "summary": summary,
            "reasoning": reasoning,
            "recommendation": recommendation,
            "object_size_ratio": float(object_size_ratio),
            "center_proximity": float(center_proximity)
        }
        
        # Save alert data locally and get paths
        local_data = save_alert_locally(frame, metadata)
        
        if local_data:
            # Add local storage info to the data we send to the alert server
            metadata["alert_id"] = local_data["alert_id"]
            metadata["evidence_path"] = local_data["image_path"]
            metadata["metadata_path"] = local_data["metadata_path"]
            metadata["local_folder"] = local_data["folder"]

        # Send alert data to alert server
        response = requests.post(ALERT_SERVER_URL, json=metadata, timeout=15)
        
        if response.status_code == 200:
            print(f"🚨 Alert sent successfully: {detected_object} (Threat Level: {threat_level:.1f})")
            print(f"✅ Summary: {summary}")
            if local_data:
                print(f"✅ Data stored locally: {local_data['alert_id']}")
        else:
            print(f"❌ Failed to send alert. Status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error sending alert: {e}")
    except Exception as e:
        print(f"❌ Unexpected error in send_alert: {e}")

def generate_frames():
    """Generates video frames with object detection."""
    global last_alert_time, verification_counter, alert_sent
    
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Error: Could not open camera")
        return
    
    print("✅ Camera initialized successfully")
    notify_main_server()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Error: Failed to capture frame")
            break
        
        try:
            # Run YOLO detection
            results = model(frame, conf=CONFIDENCE_THRESHOLD)
            
            current_time = time.time()
            detection_made = False
            
            gun_detected = False
            max_confidence = 0.0
            gun_box = None
            gun_class_name = ""

            # Process detections
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        # Get detection details
                        confidence = float(box.conf[0])
                        class_id = int(box.cls[0])
                        class_name = model.names[class_id]
                        
                        if class_name.lower() == "gun":
                            gun_detected = True
                            if confidence > max_confidence:
                                max_confidence = confidence
                                gun_box = box.xyxy[0].tolist()
                                gun_class_name = class_name
                            
                            x1, y1, x2, y2 = map(int, box.xyxy[0])  
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                            label = f"{class_name} ({confidence:.2f})"
                            cv2.putText(frame, label, (x1, y1 - 10), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                            detection_made = True
                        else:
                            # Draw bounding box and label for other detected objects
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            color = (0, 255, 0) # Green for other objects
                            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                            label = f"{class_name}: {confidence:.2f}"
                            cv2.putText(frame, label, (int(x1), int(y1) - 10), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                            detection_made = True

            if gun_detected:
                # Calculate additional metrics for threat assessment for the most confident gun detection
                frame_height, frame_width = frame.shape[:2]
                box_width = gun_box[2] - gun_box[0]
                box_height = gun_box[3] - gun_box[1]
                object_size_ratio = (box_width * box_height) / (frame_width * frame_height)
                
                # Calculate center proximity (how close to center of frame)
                box_center_x = (gun_box[0] + gun_box[2]) / 2
                box_center_y = (gun_box[1] + gun_box[3]) / 2
                frame_center_x = frame_width / 2
                frame_center_y = frame_height / 2
                
                distance_from_center = np.sqrt(
                    ((box_center_x - frame_center_x) / frame_width) ** 2 +
                    ((box_center_y - frame_center_y) / frame_height) ** 2
                )
                center_proximity = 1 - min(distance_from_center, 1)
                
                # Calculate threat level
                threat_level = calculate_threat_level(max_confidence, object_size_ratio, center_proximity)

                # Alert logic with cooldown and verification
                if current_time - last_alert_time >= ALERT_COOLDOWN:
                    if not alert_sent:
                        verification_counter += 1
                        
                        if verification_counter >= VERIFICATION_FRAMES:
                            send_alert(frame, gun_class_name, max_confidence, threat_level, 
                                     object_size_ratio, center_proximity)
                            last_alert_time = current_time
                            alert_sent = True
                            verification_counter = 0
                    else:
                        # Reset if we're still in cooldown
                        verification_counter = 0
                else:
                    verification_counter = 0
            else:
                # Reset alert flag if no gun detection
                alert_sent = False
                verification_counter = 0
            
            # Add timestamp and camera info to frame
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cv2.putText(frame, f"Camera: {CAMERA_ID} | {timestamp}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(frame, f"Location: {CAMERA_LOCATION}", 
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Encode frame for streaming
            _, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                   
        except Exception as e:
            print(f"❌ Error processing frame: {e}")
            continue
    
    cap.release()

@app.route('/video_feed')
def video_feed():
    """Video streaming route."""
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/status')
def status():
    """Health check endpoint."""
    return {
        "status": "active",
        "camera_id": CAMERA_ID,
        "location": CAMERA_LOCATION,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == '__main__':
    print(f"🚀 Starting camera detection service...")
    print(f"📹 Camera ID: {CAMERA_ID}")
    print(f"📍 Location: {CAMERA_LOCATION}")
    print(f"🎯 Confidence Threshold: {CONFIDENCE_THRESHOLD}")
    print(f"💾 Local Storage: {LOCAL_STORAGE_DIR}")
    
    app.run(host='0.0.0.0', port=5003, debug=False, threaded=True)


