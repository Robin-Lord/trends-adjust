#  TODO: Make clear that modelling is multiplicative (assumes that seasonal effects will grow/shrink with overall trend)


import streamlit as st
import pandas as pd
import numpy as np
from prophet import Prophet # type: ignore
import datetime

from typing import Tuple


def create_and_fit_prophet(
        df: pd.DataFrame,
        regressor_cols: list
        ) -> Prophet:
    
    m = Prophet(seasonality_mode="multiplicative")

    # Add monthly seasonality
    m.add_seasonality(name='monthly', period=30.5, fourier_order=5)


    # If the list is empty it shouldn't loop
    for c in regressor_cols:
        # All c should be present in dataframe
        # because they had to be selected from the
        # dropdown
        m.add_regressor(c)

    
    # Log transform data to avoid predictions that go below 0
    df_for_fit = df.copy(deep=True)
    df_for_fit["y"] = np.log(df_for_fit["y"])

    m.fit(df_for_fit)

    return m





def test_button_submit():
    st.write(":smile:")

def calculate_days_in_future(
        final_date: datetime.date,
        days_to_add: int
    ) -> datetime.date:

    future_date = final_date + datetime.timedelta(days=days_to_add)

    return future_date

def show_final_date(
        df: pd.DataFrame,
        date_col: str,
        days_to_add: int = 365
        ) -> Tuple[datetime.date, datetime.date, int]:
    
    
    first_date_of_user_data = df[date_col].min()
    last_date_of_user_data = df[date_col].max()

    last_date_of_forecast: datetime.date = calculate_days_in_future(
        final_date=last_date_of_user_data,
        days_to_add=days_to_add
    )

    # Convert dates to writeable strings
    first_user_date_str = first_date_of_user_data.strftime("%Y-%m-%d") 
    last_user_date_str = last_date_of_user_data.strftime("%Y-%m-%d")
    last_forecast_date_str = last_date_of_forecast.strftime("%Y-%m-%d")

    st.write(f"""
Your data runs from {first_user_date_str} to {last_user_date_str}  \n
We will generate a forecast from {last_user_date_str} until {last_forecast_date_str}, click 'confirm' to continue""")

    return last_date_of_user_data, last_date_of_forecast, days_to_add



def create_forecast(
        fitted_model: Prophet,
        future_data: pd.DataFrame
        ):
    

    # Start by getting prophet's broken down prediction
    forecast = fitted_model.predict(future_data)

    return forecast

def transform_forecast(
        df: pd.DataFrame,
        columns_to_adjust: list[str]
        ) -> pd.DataFrame:
    
    # Log transform predicted data (reversing earlier transform)
    # Clip values at 0 to avoid any negatives
    for c in columns_to_adjust:
        df[c] = np.exp(df[c])
        df[c] = df[c].clip(lower = 0)
        
    return df


def reverse_engineer_forecast_for_trend(
        forecast_df: pd.DataFrame,
        multiplier: float,
        ):
    
    """
    For each day - calculate what the prediction would be if trend
    for every future predicted day was exactly the same as the 
    very first day. Calculate the difference between that and actual
    and use that to be "100% trend applied".

    Take multiplier and multiply the difference by that.

    Then add the new difference onto yhat, yhat_upper, and yhat_lower.

    This logic thanks to David Westby.
    """

    # # Get the multiplier columns
    # components = ['daily', 'weekly', 'yearly', 'monthly', 'holidays']
    # components = [comp for comp in components if comp in forecast_df.columns]

    for line in ["", "_lower", "_upper"]:
        # Loop through standard, lower, and upper forecasts

        first_trend_val = forecast_df[f"trend{line}"].iloc[0]
        forecast_df[f"yhat{line}_fixed_trend"] = first_trend_val
        forecast_df[f"yhat{line}_zero_trend"] = first_trend_val


        forecast_df[f"yhat{line}_zero_trend"] *= 1+ forecast_df[f"multiplicative_terms{line}"]

        # Get the difference between new and original
        # This is "100%" difference where actual is 100
        # and no trend change is 0
        forecast_df[f"{line}_trend_diff"] = forecast_df[f"yhat{line}"]-forecast_df[f"yhat{line}_zero_trend"]

        # Multiply that difference by the multiplier
        forecast_df[f"{line}_trend_diff_to_use"] = forecast_df[f"{line}_trend_diff"]*multiplier

        # Add that difference to get final adjusted value
        # We can add because the number we're adding is multiplicative
        # if our "constant trend" value is lower than actual we'll
        # automatically subtract, if it's higher we'll automatically add on
        forecast_df[f"yhat{line}_adjusted"] = forecast_df[f"yhat{line}_zero_trend"]+forecast_df[f"{line}_trend_diff_to_use"]

    return forecast_df