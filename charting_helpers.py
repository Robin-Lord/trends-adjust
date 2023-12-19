import plotly.graph_objects as go # type: ignore
import pandas as pd
import numpy as np
import streamlit as st

def line_plot_highlighting_missing_sections(
        df: pd.DataFrame,
        future_df: pd.DataFrame,
        date_col: str,
        target_col: str) -> go.Figure:

    # Create a line chart
    fig = go.Figure()

    # Add line trace
    fig.add_trace(go.Scatter(
        x=df['ds'], 
        y=df['y'], 
        mode='lines', 
        name='y')
        )
    
    # Find first missing row
    first_missing = future_df["ds"].iloc[0]
    last_missing = future_df["ds"].iloc[len(future_df)-1]

    st.write(f"We will forecast data from {first_missing} to {last_missing}")

    fig.add_vrect(
        x0 = first_missing,
        x1 = last_missing,
        fillcolor = "red",
        opacity = 0.3,
        line_width = 0
    )

    # Set the y-axis to logarithmic
    fig.update_layout(
        yaxis_type="log", 
        title=f"Line Chart of {target_col} with Logarithmic Scale (area in red is missing data that will be forecast)",
        xaxis_title=date_col, 
        yaxis_title=target_col
        )

    # Return the figure
    return fig



def visualise_forecast(
        df: pd.DataFrame,
        target_col: str,
        date_col: str):
    
    # Create a line chart
    fig = go.Figure()

    # Add line trace
    fig.add_trace(go.Scatter(
        x=df['ds'], 
        y=df['y'], 
        mode='lines', 
        name='historic')
        )
    
    
        # Add lower bound trace for the fan (invisible)
    fig.add_trace(go.Scatter(
        x=df[date_col], 
        y=df['yhat_lower'],
        mode='lines',
        line=dict(width=0),
        showlegend=False)
    )

    # Add upper bound trace for the fan and fill the area
    fig.add_trace(go.Scatter(
        x=df[date_col], 
        y=df['yhat_upper'],
        mode='lines',
        fill='tonexty',  # Fill area between yhat_upper and yhat_lower
        line=dict(width=0),
        fillcolor='rgba(0, 100, 80, 0.2)',  # Adjust color and transparency
        showlegend=False)
    )

    
    fig.add_trace(go.Scatter(
        x=df['ds'], 
        y=df['yhat'], 
        mode='lines', 
        name='forecast')
        )
    
    # Set the y-axis to logarithmic
    fig.update_layout(
        title=f"Forecast of {target_col}",
        xaxis_title=date_col, 
        yaxis_title=target_col
        )
    


    # Return the figure
    return fig