from ultralytics import YOLO
import cv2

# Load the model
model_path = 'knife.pt'  # Path to your YOLOv8 model in the same folder
model = YOLO(model_path)

# Set detection threshold
model.conf = 0.10


def detect_and_draw(frame):
    # Run detection
    results = model(frame)

    # Process each detection
    for box in results[0].boxes:
        # Extract bounding box coordinates and label
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        confidence = box.conf[0].item()
        label = f"{box.cls[0].item()} ({confidence:.2f})"

        # Draw bounding box
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    return frame

# Video capture (replace 0 with video file path for testing)
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Process frame
    processed_frame = detect_and_draw(frame)

    # Display the frame
    cv2.imshow('Gun Detection', processed_frame)

    # Break on 'q' key press
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release resources
cap.release()
cv2.destroyAllWindows()
