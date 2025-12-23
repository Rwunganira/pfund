import streamlit as st
import plotly.graph_objects as go
import sys
import os

# Add the parent directory to the path to import Flask app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import Indicator, Activity, db

st.set_page_config(
    page_title="Indicator Progress Chart",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Indicator Progress by Year")

# All database operations need to be within Flask app context
with app.app_context():
    # Sidebar filters
    st.sidebar.header("Filters")
    
    # Get all unique implementing entities
    entities = db.session.query(Activity.implementing_entity).distinct().all()
    entity_options = [e[0] for e in entities if e[0]]
    selected_entities = st.sidebar.multiselect(
        "Implementing Entity",
        options=entity_options,
        default=[]
    )
    
    # Indicator type filter
    indicator_type = st.sidebar.selectbox(
        "Indicator Type",
        options=["All", "Quantitative", "Qualitative"],
        index=0
    )
    
    # Build query
    query = db.session.query(Indicator).join(Activity, Indicator.activity_id == Activity.id)
    
    if selected_entities:
        query = query.filter(Activity.implementing_entity.in_(selected_entities))
    
    if indicator_type != "All":
        query = query.filter(Indicator.indicator_type == indicator_type)
    
    indicators = query.all()
    
    # Calculate per-year summaries
    on_track_y1 = sum(1 for ind in indicators if ind.status_year1 == "On Track")
    at_risk_y1 = sum(1 for ind in indicators if ind.status_year1 == "At Risk")
    behind_y1 = sum(1 for ind in indicators if ind.status_year1 == "Behind")
    not_started_y1 = sum(1 for ind in indicators if not ind.status_year1 or ind.status_year1 == "Not Started")
    
    on_track_y2 = sum(1 for ind in indicators if ind.status_year2 == "On Track")
    at_risk_y2 = sum(1 for ind in indicators if ind.status_year2 == "At Risk")
    behind_y2 = sum(1 for ind in indicators if ind.status_year2 == "Behind")
    not_started_y2 = sum(1 for ind in indicators if not ind.status_year2 or ind.status_year2 == "Not Started")
    
    on_track_y3 = sum(1 for ind in indicators if ind.status_year3 == "On Track")
    at_risk_y3 = sum(1 for ind in indicators if ind.status_year3 == "At Risk")
    behind_y3 = sum(1 for ind in indicators if ind.status_year3 == "Behind")
    not_started_y3 = sum(1 for ind in indicators if not ind.status_year3 or ind.status_year3 == "Not Started")
    
    # Create stacked bar chart with Plotly
    fig = go.Figure()
    
    years = ['Year 1', 'Year 2', 'Year 3']
    colors = {
        'Not Started': '#6b7280',
        'Behind': '#ef4444',
        'At Risk': '#f59e0b',
        'On Track': '#10b981'
    }
    
    # Add stacked bars
    fig.add_trace(go.Bar(
        name='Not Started',
        x=years,
        y=[not_started_y1, not_started_y2, not_started_y3],
        marker_color=colors['Not Started'],
        text=[not_started_y1, not_started_y2, not_started_y3],
        textposition='inside',
        textfont=dict(color='white', size=10, family='Arial Black')
    ))
    
    fig.add_trace(go.Bar(
        name='Behind',
        x=years,
        y=[behind_y1, behind_y2, behind_y3],
        marker_color=colors['Behind'],
        text=[behind_y1, behind_y2, behind_y3],
        textposition='inside',
        textfont=dict(color='white', size=10, family='Arial Black')
    ))
    
    fig.add_trace(go.Bar(
        name='At Risk',
        x=years,
        y=[at_risk_y1, at_risk_y2, at_risk_y3],
        marker_color=colors['At Risk'],
        text=[at_risk_y1, at_risk_y2, at_risk_y3],
        textposition='inside',
        textfont=dict(color='white', size=10, family='Arial Black')
    ))
    
    fig.add_trace(go.Bar(
        name='On Track',
        x=years,
        y=[on_track_y1, on_track_y2, on_track_y3],
        marker_color=colors['On Track'],
        text=[on_track_y1, on_track_y2, on_track_y3],
        textposition='inside',
        textfont=dict(color='white', size=10, family='Arial Black')
    ))
    
    # Update layout - smaller size
    fig.update_layout(
        barmode='stack',
        title={
            'text': 'Progress Status by Year',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 12, 'family': 'Arial'}
        },
        xaxis_title="Year",
        yaxis_title="Number of Indicators",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=9)
        ),
        height=300,
        margin=dict(l=40, r=40, t=60, b=40),
        plot_bgcolor='white',
        paper_bgcolor='white',
        xaxis=dict(tickfont=dict(size=9)),
        yaxis=dict(tickfont=dict(size=9))
    )
    
    # Display chart in a smaller container (top right corner style)
    col_chart, col_empty = st.columns([2, 1])
    with col_chart:
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    
    # Display summary statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Indicators", len(indicators))
    
    with col2:
        total_on_track = on_track_y1 + on_track_y2 + on_track_y3
        st.metric("On Track (Total)", total_on_track)
    
    with col3:
        total_at_risk = at_risk_y1 + at_risk_y2 + at_risk_y3
        st.metric("At Risk (Total)", total_at_risk)
    
    with col4:
        total_behind = behind_y1 + behind_y2 + behind_y3
        st.metric("Behind (Total)", total_behind)
