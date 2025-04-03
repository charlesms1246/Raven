# Real-time Accident & Vigilance Enhanced-Surveillance Network (RAVEN) 

## Overview
Chennai's rapid urbanization and increasing traffic congestion necessitate intelligent systems to enhance road safety and streamline traffic. This AI/ML-based application offers an integrated solution that combines real-time hazard detection, accident monitoring, and emergency response. It provides a user-friendly interface for government officials to manage traffic efficiently. Leveraging cutting-edge AI/ML technologies and data analytics, the application ensures safer roads, quicker emergency response, and better traffic management.

## Features

### 1. Real-Time Hazard Detection and Notification
- AI-powered image recognition monitors road conditions using cameras placed at key locations.
- Detects hazards such as potholes, oil spills, and fallen debris.
- ML models classify hazards and notify relevant authorities.
- Road users receive push notifications with hazard locations and alternative routes.

### 2. Accident Detection and Emergency Response
- Integrates accelerometer data from connected vehicles and smartphones with real-time video feeds.
- AI algorithms detect abnormal vehicle behavior to identify potential accidents.
- Automatically alerts emergency services with accident location, severity, and nearby hospitals.
- Predictive models prioritize responses based on severity and resource proximity.

### 3. Smart Detection of Road Hazards
- Deep learning models identify unauthorized parking, jaywalking, and traffic violations in real time.
- Object detection and pattern recognition ensure accurate identification.
- Collaborates with weather monitoring stations to predict weather-related hazards (e.g., waterlogging during heavy rains).
- Provides timely warnings to drivers and road users.

### 4. Interactive Traffic Management Interface for Government Officials
- Intuitive dashboard displaying real-time traffic data, accident reports, and hazard notifications.
- **Heatmaps:** Highlights congestion areas and traffic flow.
- **Incident Management:** Enables officials to assign tasks to field staff or emergency services.
- **Traffic Signal Optimization:** AI-based adjustments of traffic light timings to enhance flow.
- **Data Insights:** Provides actionable insights through historical data analytics to plan infrastructure improvements and regulations.

## Technology Stack
- **Languages Used:** Python, Java, JavaScript, MongoDB
- **Libraries & Tools:** YOLOv11, OpenCV
- **Data Collection:** Public datasets, traffic cameras, GPS devices, weather monitoring systems
- **AI/ML Models:**
  - Convolutional Neural Networks (CNNs) for image processing
  - Recurrent Neural Networks (RNNs) for pattern prediction
  - Reinforcement learning for traffic signal optimization
- **Mobile Application:** User-friendly app for drivers and pedestrians to receive alerts and updates

## Installation

### Prerequisites
- Python 3.10+
- Java 21+
- Node.js for web interface
- MongoDB for data storage
- Virtual environment (Python) setup:
  ```sh
  python -m venv venv
  source venv/bin/activate  # On Windows use 'venv\Scripts\activate'
  ```

### Setup
1. Clone the repository:
   ```sh
   git clone https://github.com/charlesms1246/Raven.git
   cd Raven
   ```
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
3. Set up the database:
   ```sh
   mongod --dbpath ./data/db
   ```
4. Run the application:
   ```sh
   python app.py
   ```

## Impact
This AI/ML-based system fosters a safer, more efficient urban environment in Chennai. By reducing emergency response times, minimizing road hazards, and optimizing traffic flow, the application enhances overall quality of life. For government officials, it provides a centralized platform for managing traffic and safety, promoting Chennai as a smart city model.

## Contributing
Contributions are welcome! Follow these steps to contribute:
1. Fork the repository.
2. Create a new branch (`git checkout -b feature-name`).
3. Commit your changes (`git commit -m 'Added new feature'`).
4. Push to the branch (`git push origin feature-name`).
5. Open a pull request.

