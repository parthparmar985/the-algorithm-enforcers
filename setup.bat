@echo off
echo ==============================================
echo Installing Backend Dependencies...
echo ==============================================
cd backend
python -m venv venv
call venv\Scripts\activate.bat
pip install -r requirements.txt
cd ..

echo ==============================================
echo Installing Frontend Dependencies...
echo ==============================================
cd frontend
call npm install
cd ..

echo ==============================================
echo Setup Complete! Ensure you have a 'ai_cctv' database in XAMPP phpMyAdmin.
echo Then you can double click 'run.bat' to start the servers.
pause
