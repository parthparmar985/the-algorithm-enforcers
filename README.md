# AI CCTV Intelligence & Surveillance Platform

A complete, working AI-powered CCTV Surveillance & Police Intelligence System built as a hackathon MVP. The framework is entirely functional and operates locally using XAMPP MySQL, FastAPI, React, YOLO, and EasyOCR.

## Important Disclaimer & Privacy Note
> **This is a hackathon prototype.**
> Real CCTV deployment requires specialized legal authorization. CCTV data must be handled in accordance with privacy laws and policies. Production deployments necessitate strong access controls. AI outputs are **strictly indicators** and should not be used alone to determine criminality. No facial recognition is implemented in this MVP.

## Tech Stack
**Frontend:** React.js, Vite, Tailwind CSS, Recharts, React Router
**Backend:** Python, FastAPI, SQLAlchemy, WebSockets
**Database:** MySQL (via XAMPP)
**AI Engine:** OpenCV, Ultralytics YOLOv11, ByteTrack, EasyOCR

---

## ⚡ Setup Instructions

### 1. Database Setup (XAMPP)
1. Open **XAMPP Control Panel**.
2. Start the **Apache** and **MySQL** modules.
3. Open a browser and navigate to `http://localhost/phpmyadmin`.
4. Create a new empty database named `ai_cctv` (if not already done).

### 2. Backend Setup
1. Navigate to the `backend` directory: `cd backend`
2. Create virtual environment: `python -m venv venv`
3. Activate it:
   - Windows: `.\venv\Scripts\activate`
4. Install dependencies: `pip install -r requirements.txt`
   - *Note: YOLO weights (`yolo11n.pt`) will automatically download on first execution.*
   - *EasyOCR requires CPU capabilities defaulting to OpenCV execution.*
5. Start the server: `uvicorn app.main:app --reload`
   - The ORM models will automatically build the tables inside MySQL on the first boot.

### 3. Frontend Setup
1. Navigate to the `frontend` directory: `cd frontend`
2. Install dependencies: `npm install`
3. Run Vite server: `npm run dev`
4. Open the browser to `http://localhost:5173`.

---

## 🚀 Hackathon Demo Workflow

To successfully demonstrate this project to judges, follow this sequence:

1. **Start all services**: XAMPP MySQL, FastAPI backend, Vite frontend.
2. **Access Command Center**: Go to the frontend URL.
3. **Login**: Use an API platform (like Postman or cURL) to hit `POST http://localhost:8000/api/auth/register` with `{ "name": "Admin", "email": "admin@police.local", "password": "password", "role": "ADMIN" }`. Log in through the UI.
4. **Dashboard View**: Show the sleek dashboard. Statistics will initially be empty.
5. **Add Camera**: Go to **Manage Cameras**, add a new entry (e.g. "Main Gate", "CAM-01").
6. **Upload Footage**: Navigate to **Video Upload**. 
   - Upload a sample `.mp4` video containing moving vehicles.
   - Select your configured camera from the dropdown, then click **Start AI Inference Engine**.
7. **AI in Action**:
   - The FastAPI background process will run YOLO object detection and ByteTrack seamlessly.
   - The engine automatically saves snapshots, writes vehicle plates, and triggers rules.
8. **Real-time Alerts**: The React UI will automatically flash a notification for tracked items interacting with the mock rules (e.g., stationary triggers).
9. **Search**: Go to **Investigation** and view the analytics/table outputs.
10. **Review DB**: Open `phpMyAdmin` to show the backend structure stored locally without hardcoded logic.
