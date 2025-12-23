@echo off
echo Starting Streamlit app for Indicator Progress Chart...
echo.
echo Make sure you have installed: pip install streamlit plotly
echo.
streamlit run streamlit_app.py --server.port 8501 --server.headless true
pause

