# Streamlit Chart Integration

This project includes a Streamlit app for visualizing indicator progress charts.

## Installation

First, install Streamlit and Plotly:

```bash
pip install streamlit plotly
```

Or install all dependencies:

```bash
pip install -r requirements.txt
```

## Running the Streamlit App

### Option 1: Standalone Streamlit App

Run the Streamlit app independently:

**Windows:**
```bash
run_streamlit.bat
```

**Linux/Mac:**
```bash
chmod +x run_streamlit.sh
./run_streamlit.sh
```

**Or directly:**
```bash
streamlit run streamlit_app.py
```

This will start a Streamlit server (usually on http://localhost:8501) where you can view the interactive chart with filters in a sidebar.

### Option 2: Embedded in Flask (via iframe)

1. Start the Streamlit app on port 8501:
```bash
streamlit run streamlit_app.py --server.port 8501 --server.headless true
```

2. In another terminal, start your Flask app:
```bash
python app.py
```

3. Navigate to the Indicator Progress page in your Flask app. The Streamlit chart will be embedded in the top-right corner via iframe.

4. To use Streamlit iframe instead of Plotly, uncomment the iframe section in `templates/indicator_progress.html` and comment out the Plotly div.

### Option 3: Use Plotly directly in Flask (Current Default)

The Flask app currently uses Plotly to generate charts directly. The chart is embedded without needing a separate Streamlit server. This is the recommended approach for production.

To switch to Streamlit iframe:
1. Uncomment the iframe section in `templates/indicator_progress.html` (around line 122)
2. Comment out the Plotly div section
3. Make sure Streamlit is running on port 8501

## Files

- `streamlit_app.py` - Main Streamlit application for indicator progress visualization
- `streamlit_chart.py` - Alternative Streamlit implementation (can be removed)
- `activity_routes.py` - Flask route that generates Plotly charts (current default)
- `run_streamlit.bat` - Windows batch file to start Streamlit
- `run_streamlit.sh` - Linux/Mac script to start Streamlit

## Features

The Streamlit app provides:
- Interactive stacked bar chart showing progress by year
- Sidebar filters for implementing entity and indicator type
- Summary metrics (Total, On Track, At Risk, Behind)
- Real-time filtering and chart updates

## Dependencies

Required packages (already in `requirements.txt`):
- `streamlit==1.39.0`
- `plotly==5.22.0`
