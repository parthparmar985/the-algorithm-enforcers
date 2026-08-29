@echo off
echo ==============================================
echo Starting AI CCTV Platform...
echo ==============================================

echo Make sure you have started MySQL inside XAMPP!
pause

echo Starting Backend Server in a new window...
start "FastAPI Backend" cmd /k "cd backend && call venv\Scripts\activate.bat && uvicorn app.main:app --reload"

echo Starting Frontend Server in a new window...
start "React Frontend" cmd /k "cd frontend && npm run dev"

echo Both services have been launched in separate windows!
echo Once Vite finishes loading, go to http://localhost:5173
pause
