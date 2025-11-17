@echo off
echo 🏥 Health Insurance Data Generator
echo ================================
echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Starting Streamlit application...
streamlit run streamlit_app.py

pause