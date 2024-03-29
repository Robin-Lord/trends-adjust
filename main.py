import streamlit as st
import st_helpers as sth
import pandas as pd
import process_forecast as pf
import pandas_helpers as pdh
import seaborn as sns #type: ignore
import charting_helpers as ch
import datetime as datetime
import handle_holiday_list as hh

# Tracking decorator
import ga4py.add_tracker as add_tracker
from ga4py.custom_arguments import MeasurementArguments

from typing import Union, Tuple

# Error handling

import logging

def add_custom_css():
        # Wr
    custom_css = """
    <style>

    @keyframes bounce {
        10%, 11%, 14% {
            transform: translateY(0);
        }
        12% {
            transform: translateY(-20px);
        }
        13% {
            transform: translateY(-10px);
        }
    }

    button[kind="primary"] {
        color: #216a82;
        border-color: #216a82;
        width: 50%;   /* Increase button width */
        height: 50px;   /* Increase button height */
        font-size: 20px; /* Increase font size */
        animation: bounce 10s infinite; /* Add bouncing animation */
    }
    
    </style>
    """

    # Inject custom CSS with markdown
    st.markdown(custom_css, unsafe_allow_html=True)


def show_upload_expander_contents():
    if st.session_state.uploaded_file == None:
        st.session_state.uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
        st.session_state.data_checked = False
    else:
        st.write(f"Uploaded file: {st.session_state.uploaded_file}")

def handle_uploaded_file() -> Tuple[pd.DataFrame, str, str, list]:
    
        # Reset upload section
    if st.session_state.step == "upload":
        st.session_state.step = "columns"

        # Read file
        data = pd.read_csv(st.session_state.uploaded_file)

        # Add tracking at this point of the process, as a sign a user has started using the tool
        tracking_args_dict = st.session_state.basic_tracking_info.copy()
        tracking_args_dict["skip_stage"] = ["start", "end"]
        tracking_args_dict["stage"] = "upload_file"

        # Check it has the right columns
        pdh.check_columns(data, ga4py_args_remove = tracking_args_dict)

        st.session_state.file_data = data


        st.experimental_rerun()

    # Read and display the data
    data = st.session_state.file_data
    st.write("""### Example top and bottom rows of your CSV:
Use these to make sure everything looks right.             

*First 5rows:*
             """)
    st.write(data.head())
    st.write("*Last 5 rows:*")
    st.write(data.tail())

    # Logic for choosing columns
    if "date_col_index" not in locals():
        # Only set these if needed to avoid dropdown update issues
        (
            default_date_col, 
            date_col_index,
            target_metrics_options, 
            default_target_metric_col, 
            target_metric_col_index,
            regressor_options, 
            default_regressor_cols,
            ) = pdh.choose_columns(df = data) 
        

    # Show column choosers
    columns_expander = st.expander(label= "Select columns", expanded=st.session_state.step == "columns")
    with columns_expander:
    
        # Selection for Date column
        st.session_state.date_col = st.selectbox("""Select the Date column (by default will select any column called 'Date'):""", 
                                        options=data.columns, 
                                        index=date_col_index, 
                                        disabled=st.session_state.step != "columns"
                                        )
        
        date_col = st.session_state.date_col

        # Selection for Target Metric column
        st.session_state.target_metric_col = st.selectbox("Select the Target Metric column:", 
                                        options=target_metrics_options, 
                                        index= target_metric_col_index, 
                                        disabled=st.session_state.step != "columns"
                                        )
        
        target_metric_col = st.session_state.target_metric_col

        # Selection for Regressor columns
        st.session_state.regressor_col_list = st.multiselect("**Optional** select Regressor columns:", 
                                        options=regressor_options,
                                        default=default_regressor_cols, 
                                        disabled=st.session_state.step != "columns"
                                        )
        
        regressor_cols = st.session_state.regressor_col_list


        available_countries = hh.return_available_countries()

        st.session_state.holiday_country = st.selectbox("**Optional** choose country (this will automatically pull in some basic holidays for that country which can help the Machine Learning understand seasonal patterns better):", 
                                        options=available_countries,
                                        disabled=st.session_state.step != "columns"
                                        )
        

        # Checkbox with a label and tooltip
        st.session_state.use_log_scale = st.checkbox(
            'Use log scale', 
            help='Sometimes Machine Learning forecasts can give unhelpful answers (i.e. predicting negative traffic based on a past trend). Using a log scale can help you avoid that problem',
            value=False,
            disabled=st.session_state.step != "columns")
        

        
        # Force state update to flush through change 
        # (streamlit seems to need a second) update
        if (
            st.session_state.date_col != default_date_col
            or 
            st.session_state.target_metric_col != default_target_metric_col
            or 
            st.session_state.regressor_col_list != default_regressor_cols
            ):

            print(f"""
st.session_state.date_col != default_date_col: {st.session_state.date_col != default_date_col}
st.session_state.target_metric_col != default_target_metric_col: {st.session_state.target_metric_col != default_target_metric_col}
st.session_state.regressor_col_list != default_regressor_cols: {st.session_state.regressor_col_list != default_regressor_cols}
""")
            st.experimental_rerun()


        # Display chosen categories
        st.write("You categorized the columns as follows:")
        st.write(f"Date column: {date_col}")
        st.write(f"Target Metric column: {target_metric_col}")
        st.write(f"Regressor columns: {', '.join(regressor_cols) if regressor_cols else 'None'}")
        st.write(f"Target country (for automatically including national holidays in ML context): {st.session_state.holiday_country}")

        # Display button to submit data
        user_clicks_submit = st.button("Submit")
        if user_clicks_submit:
            sth.update_step_state(previous_step = "columns", new_step = "dates")
        
        return data, date_col, target_metric_col, regressor_cols


def handle_dates_checks(data, date_col, target_metric_col, regressor_cols):
# Handle date column
        (current_data,
            future_data,
            current_plus_future) = pdh.check_and_convert_data(
            df = data, 
            date_col=date_col,
            target_col=target_metric_col,
            regressor_cols=regressor_cols
            )
        
        if st.session_state.data_checked:
            # Only continue if all the data checks are fine

            fig = ch.line_plot_highlighting_missing_sections(
                df = current_plus_future,
                future_df=future_data,
                date_col = date_col,
                target_col = target_metric_col)
            
            st.plotly_chart(fig)
            
            continue_with_dates = st.button("Confirm")

            if continue_with_dates:
                sth.update_step_state(previous_step = "dates", new_step = "forecast")
            
        
        return current_data, future_data, date_col, target_metric_col, regressor_cols


@add_tracker.analytics_hit_decorator
def main() -> None:


    add_custom_css()

    st.title("Forecast with adjustable trend")

    st.image("assets/aira_logo.png", caption='Aira Digital Marketing', width=150)



    st.markdown("""# Aira's flexible Machine Learning forecasting tool
                                    
Welcome to Aira's flexible forecasting tool!
                
Use this tool to create flexible Machine Learning forecasts based on past data. 
                
Then you can make adjustments to the expected trend based on your own knowledge, while preserving things like seasonal patterns found in your data.
                """) 
        
    what_is = st.expander(label="What is this tool and what is it for?", expanded = False)
    with what_is:
        st.markdown("""## What is this tool and what is it for?""")
        st.image("assets/facebook-prophet-logo.png")            

        st.markdown(                    
"""This is a forecasting tool based on [Facebook's Prophet](https://facebook.github.io/prophet/).
                    
It uses Machine Learning to look at your historic data and forecast what future data might look like.
                    
Tools like Prophet are a very powerful way to create a forecast which handles things like weekly, monthly, yearly, seasonality as well as trends over time.

(Like if your business is growing year-on-year you want to be able to factor in that trend *as well as* the fact that, say, every January is a very low month and you should expect it to be low nomatter how much you grow).
""")
        

        st.image("assets/cycle-chart.png")
        st.markdown("Image from the [Facebook Prophet research paper](https://peerj.com/preprints/3190/)")
        st.markdown("""                    
                    
                    
**The downside of these tools is that they can end up relying *too much* on past trends.** 

Often we know something that is likely to change from this year to the next, i.e. 
- We know that growth will slow down because of industry size
- We know there's a recession looming
- We have been able to change things whic should stop year-on-year loss.
                    
While tools like Prophet have some ways of communicating that (most often 'regressors' which you can still use with this tool), it can sometimes be very hard to communicate to the code that you want it to keep all of the smart seasonality stuff which it is so hard for humans to put together, but you need it to *just ease off a bit* in its enthusiastic upwards or downwards trend.
                    
[David Westby has written about this problem](https://aira.net/blog/an-easier-way-to-make-machine-learning-forecasts-smarter/) on the Aira blog, particularly how it relates to marketing forecasting, so if you want to read more, check that out.""")
        st.image("assets/david-forecasting-blog.png")

        st.markdown("""

This tool was created by the Aira Innovations team (based on logic that Dave came up with) to help ease off on forecasts which are too strong in one direction or another.
                    
If first works out what the forecast would be if we assume baseline performance stays exactly the same as it is on the very first day of the forecast (so doesn't go up and down) while keeping all of the seasonal effects. Then it compares that forecast to the standard one and gives you a slider so you can adjust how strongly you want the trend to apply.

It *might* feel like you're adding your biases into a perfect Machine Learning system but, shock horror, tools like Prophet are basically just a scalable way to make assumptions, they assume things like "the trends I've seen up until now will continue", and there is no great way to get them to understand a change they have never seen before. So yea - you're adding in your assumptions and biases, but yours are just as legitimate as long as you've thought about them properly!
                    
Thanks for reading! Lots of love
                    
**Aira Innovation Team**
                    
                    """)
        
        # Create two columns for the bios
        d, r = st.columns(2)

        with d:
            st.image("assets/David-Westby.jpg")
            st.markdown("""
**[David Westby](https://www.linkedin.com/in/dawestby/)**
                        
*Senior Data and Insights Consultant*
                                            
Originator of the "percent of trend" logic.
                        
                        """)            
            
        with r:
            st.image("assets/Robin.jpg")
            st.markdown("""
**[Robin Lord](https://www.linkedin.com/in/robin-lord-9906b85a/)**
                        
*Assoc. Director of Innovations*
                                            
Developed this tool.
                        
                        """)
            
    

    what_do_i_need = st.expander(label="What do I need to do?", expanded = False)
    with what_do_i_need:
        st.markdown("""## What do I need to do?

Upload a CSV file which has at least two columns:
                    
|     Date                   | Historic data for whatever number you want to forecast|
|----------------------------|-------------------------------------------------------|
| {date in yyyy-mm-dd format}|    (always a number, can be whole number or decimal   |
| {date in yyyy-mm-dd format}|    (always a number, can be whole number or decimal   |
| {date in yyyy-mm-dd format}|    (always a number, can be whole number or decimal   |

                    
- You can call your date column and target number column whatever you want, you will have a chance to select them once you've uploaded your data
- You have to have a valid yyyy-mm-dd date in every single row
- Unless you are leaving a gap at the end for the forecast (see below), you have to have a number in every single row of your "number to forecast" column
                    
If you fill every row of your uploaded data, we'll automatically create a forecast for the next 3 years (and then you can use as much or as little of it as you want)

### Leaving some rows blank

You can choose to leave a bunch of blank rows at the end, something like this
                    
|     Date                   | Historic data for whatever number you want to forecast|
|----------------------------|-------------------------------------------------------|
| {date in yyyy-mm-dd format}|    (always a number, can be whole number or decimal   |
| {date in yyyy-mm-dd format}|    (always a number, can be whole number or decimal   |
| {date in yyyy-mm-dd format}|                                                       |
| {date in yyyy-mm-dd format}|                                                       |
| {date in yyyy-mm-dd format}|                                                       |
| {date in yyyy-mm-dd format}|                                                       |
| {date in yyyy-mm-dd format}|                                                       |
                    

If you do, we'll create a forecast for just the rows you've left blank. You can do that if you want to get a forecast which is more/less than 3 years.

### Regressors                    

You can also do that if you want to use *regressors*. Regressors are a way to highlight patterns in the data so that Prophet can use them to make the forecast more accurate.

Regressors can be particularly useful here because, if you put the right regressors in, you might not *have* to manually adjust the trend with a tool like this. Regardless - you have the option here to select "100% trend" which means "use the exact numbers that Prophet came out with" so if you choose the right regressors and don't have to manually adjust the trend then all the better.

The reason you need to be able to leave blank rows for regressors is that regressors are a way to highlight past patterns *and then tell Prophet how those patterns will continue into the future*. So you *have* to tell Prophet what you think the regressors will be during your forecast period or they won't be any help at all.
                    
A dataframe with regressors might look something like this:

                    
|     Date                   | Historic data for whatever number you want to forecast|   regressor_1  | regressor_2  |
|----------------------------|-------------------------------------------------------|----------------|--------------|
| {date in yyyy-mm-dd format}|    (always a number, can be whole number or decimal   |      1         |      0       |
| {date in yyyy-mm-dd format}|    (always a number, can be whole number or decimal   |      1         |      0       |
| {date in yyyy-mm-dd format}|    (always a number, can be whole number or decimal   |      1         |      0       |
| {date in yyyy-mm-dd format}|    (always a number, can be whole number or decimal   |      0         |      10      |
| {date in yyyy-mm-dd format}|    (always a number, can be whole number or decimal   |      0         |      5       |
| {date in yyyy-mm-dd format}|    (always a number, can be whole number or decimal   |      0         |      5       |
| {date in yyyy-mm-dd format}|                                                       |      1         |      0       |
| {date in yyyy-mm-dd format}|                                                       |      1         |      0       |
| {date in yyyy-mm-dd format}|                                                       |      1         |      0       |
| {date in yyyy-mm-dd format}|                                                       |      1         |      0       |
| {date in yyyy-mm-dd format}|                                                       |      1         |      0       |                    
                    

                    
**If you want to see some example data you can use - check out the "Example Data" tab below.**
                    
                    """)
    example_data_tab = st.expander(label="Example data", expanded = False)
    with example_data_tab:

        st.markdown("""## Example Data""")

        example_data = pd.read_csv("tests/test_files/example_data_for_users_2.csv")

        st.write(example_data.head())

        example_csv = sth.convert_df(example_data)   

        st.markdown("""

If you want some example data to get started with/play around with - feel free to download and use this example data.""")
                    
        st.download_button(
        f"Download example data",
        example_csv,
        f"Example data for forecast.csv",
        f"Example data for forecast/csv",
        key='download-example-csv'
        )

        st.markdown("""The regressor column isn't doing anything at the moment but it should give you an example of what format should work.
                    
Download it here and then upload it to the tool below to begin.

If you need more information about how exactly you use this tool, check out the "What do I need to do?" section above.
""")


        
    easier_way = st.expander(label="I'm not sure what I'm doing, is there an easier way?", expanded = False)
    with easier_way:
        st.markdown("""## This seems complicated, is there an easier way?
                    
You have a couple of options:
                    
1. You could **[work with Aira!](https://www.aira.net/)** we don't do forecasting as a stand alone service but if you're planning marketing activity we can help you plan it and, as part of that, we'll do much more advanced forecasting than this (which includes things like expected impact from different activity).

2. You could try other tools, i.e. Richard Fergie's excellent [Forecast Forge](https://www.forecastforge.com/) which integrates directly into Google Sheets. Forecast Forge also has a lot of helpful resources on how to approach this kind of forecasting.

                    
                    """)


    

    user_clicks_submit = False


    # Set session states to track which part of the process we're in
    if "step" not in st.session_state:
        # Step defaults
        st.session_state.step = "upload"

        # Flag for if file uploaded
        st.session_state.uploaded_file = None
        st.session_state.file_data = None

        # Column defaults
        st.session_state.date_col = None
        st.session_state.target_metric_col = None
        st.session_state.regressor_col_list = None
        st.session_state.holiday_country = "None"

        # Basic information for tracking hits
        basic_tracking_info: MeasurementArguments = {
            # "testing_mode": True,
            "page_location": "python_trends_adjusting", 
            "page_title": "python trends adjusting", 
            "logging_level": "all",
        }

        st.session_state.basic_tracking_info = basic_tracking_info


    # File uploader
    upload_expander = st.expander(label = "Upload file", expanded=st.session_state.step == "upload")
    with upload_expander:
        show_upload_expander_contents()

    if st.session_state.uploaded_file is not None:
        data, date_col, target_metric_col, regressor_cols = handle_uploaded_file()

    # Process data
    if st.session_state.step == "dates":

        # Show column choosers
        dates_expander = st.expander(label= "Check forecast dates", expanded=st.session_state.step == "dates")

        with dates_expander:
            (current_data, 
             future_data, 
             date_col, 
             target_metric_col, 
             regressor_cols
             ) = handle_dates_checks(
                    data = data, 
                    date_col = date_col, 
                    target_metric_col = target_metric_col, 
                    regressor_cols = regressor_cols
                    )
            
            st.session_state.current_data = current_data 
            st.session_state.future_data = future_data

    if st.session_state.step == "forecast":

        current_data = st.session_state.current_data
        future_data = st.session_state.future_data
        date_col = st.session_state.date_col
        target_metric_col = st.session_state.target_metric_col
        regressor_cols = st.session_state.regressor_col_list

        # Avoid retraining if not necessary
        if "prophet_model" not in st.session_state:
            # Train model
            st.session_state.prophet_model = pf.create_and_fit_prophet(
                df = current_data,
                regressor_cols = regressor_cols,
            )

            # Add tracking at this point of the process, as a sign a user is getting their forecast
            tracking_args_dict = st.session_state.basic_tracking_info.copy()
            tracking_args_dict["skip_stage"] = ["start", "end"]
            tracking_args_dict["stage"] = "generate_forecast"

            # Make prediction
            st.session_state.prophet_forecast = pf.create_forecast(
                        fitted_model = st.session_state.prophet_model,
                        future_data = future_data,
                        ga4py_args_remove = tracking_args_dict
                        )
        
        prophet_forecast = st.session_state.prophet_forecast


        forecast_expander = st.expander(label = "Run forecast", expanded=st.session_state.step == "forecast")

        # Calculate the granularity options

        with forecast_expander:

            if "default_trend_adjustment" not in st.session_state:
                st.session_state.default_trend_adjustment = 100

            st.markdown(f"""
                        
### Adjust trend

Your Machine Learning forecast is below. **The 'trend' is applied at {st.session_state.default_trend_adjustment}% strength.**                        

Use the slider below to adjust the forecast trend. 
                        
None of the seasonality patterns will be changed but the general trend of change over time is dampened based on your knowledge of the business.

Adjust the slider if you think that trend is too strong or too weak, when you're done - download the data!
                        
                        
                        """)

            # Adjust prediction
            trend_adjustment = st.slider(
                label = "trend adjustment",
                min_value = 0,
                max_value = 100,
                value = 100,
                step = 5,
                format="%d%%"
                )/100
            
            
            trend_percent = int((trend_adjustment/1)*100)

            # Checkbox with a label and tooltip
            scale_bounds = st.checkbox(
                'Scale bounds with trend', 
                help='When you adjust the trend the bounds will normally stay the same distance from the prediction line as they normally would be. If if you want the bounds to scale along with the trend tick this box.',
                value = True)
            
            if trend_percent!= st.session_state.default_trend_adjustment:
                st.session_state.default_trend_adjustment = trend_percent
                st.experimental_rerun()
            
            adjusted_forecast = pf.reverse_engineer_forecast_for_trend(
                forecast_df = prophet_forecast,
                multiplier = trend_adjustment,
                scale_bounds = scale_bounds
            )

            # For now - just change the adjusted values to replace the current
            # values, in the future might want to be able to show current and adjusted
            # at the same time
            adjusted_forecast_for_show = adjusted_forecast.copy(deep=True)


            for c in ["yhat", "yhat_lower", "yhat_upper"]:
                adjusted_forecast_for_show[c] = adjusted_forecast_for_show[f"{c}_adjusted"]
            
            # Make sure we refuse the earlier log transform so our forecast is on the 
            # same scale as the input data
            adjusted_forecast_for_show = pf.transform_forecast(
                df = adjusted_forecast_for_show,
                columns_to_adjust=["yhat", "yhat_lower", "yhat_upper"]
            )



            # Join original and prediction together
            for_chart = pd.concat([current_data, adjusted_forecast_for_show])


            for_chart["ds"] = pd.to_datetime(for_chart["ds"]).dt.date

            # Give user an option of selecting the first and last dates to show
            # so they can keep the chart filtered
            earliest_date = for_chart["ds"].min()
            default_first_date_to_show = earliest_date
            if "default_first_date_to_show" in st.session_state:
                default_first_date_to_show = st.session_state.default_first_date_to_show
            
            latest_date = for_chart["ds"].max()
            default_last_date_to_show = latest_date
            if "default_last_date_to_show" in st.session_state:
                default_last_date_to_show = st.session_state.default_last_date_to_show

            st.write("""
-------------
### Preview data                    
Choose dates to filter the chart below (this won't change your data)""")

            # Create two columns for the date pickers
            col1, col2 = st.columns(2)


            with col1:
                first_date_to_show = st.date_input(
                    "Earliest date to show",
                    value = default_first_date_to_show,
                    min_value=earliest_date,
                    max_value=latest_date-datetime.timedelta(days = 1)
                    )
                
                if "default_first_date_to_show" not in st.session_state:
                    st.session_state.default_first_date_to_show = first_date_to_show
            with col2:

                if default_last_date_to_show<first_date_to_show: 
                    default_last_date_to_show = first_date_to_show

                last_date_to_show = st.date_input(
                    "Latest date to show",
                    value = default_last_date_to_show,
                    min_value=first_date_to_show, # type: ignore
                    max_value=latest_date
                ) 
                if "default_last_date_to_show" not in st.session_state:
                    st.session_state.default_last_date_to_show = last_date_to_show

            # Force state update to flush through change 
            # (streamlit seems to need a second) update
            if (
                st.session_state.default_last_date_to_show != last_date_to_show
                or 
                st.session_state.default_first_date_to_show != first_date_to_show
                ):

                st.session_state.default_last_date_to_show = last_date_to_show
                st.session_state.default_first_date_to_show = first_date_to_show
                st.experimental_rerun()


            if last_date_to_show<=first_date_to_show: # type: ignore
                if first_date_to_show == latest_date:
                    first_date_to_show = first_date_to_show-datetime.timedelta(days = 2) # type: ignore
                # Make sure users can't accidentally over-filter table
                last_date_to_show = first_date_to_show+datetime.timedelta(days=1) # type: ignore

            filtered_for_chart = for_chart[
                for_chart["ds"]>=first_date_to_show
                ]

            filtered_for_chart = filtered_for_chart[
                filtered_for_chart["ds"]<=last_date_to_show 
                ]


            filtered_for_chart = filtered_for_chart[["ds", "y", "yhat", "yhat_lower", "yhat_upper"]]

            forecast_fig = ch.visualise_forecast(
                            df = filtered_for_chart,
                            target_col = target_metric_col,
                            date_col = date_col)
            

            st.plotly_chart(forecast_fig)   


            # Give user the option to download their forecast data
            unfiltered_for_download = for_chart[
                ["ds", "y", "yhat", "yhat_upper", "yhat_lower"]
                ]
            
            unfiltered_for_download = unfiltered_for_download.rename(
                columns={
                "ds": date_col, 
                "y": target_metric_col,
                "yhat": f"{target_metric_col}_forecast",
                "yhat_upper": f"{target_metric_col}_upper",
                "yhat_lower": f"{target_metric_col}_lower",
                }
                )
            
            csv = sth.convert_df(unfiltered_for_download)

            st.markdown(f"""
-------------
                        
### Download data

                        
Click download to download your forecast, assuming trend is applied at {trend_percent}% strength.

If you want a way to visualise your forecast, you can download the plot above as a png by clicking on the "download plot" button just above the chart.

Or you can use [Dave Westby's blog post here to create your own chart with this data in Google Sheets.](https://aira.net/blog/forecasting-and-importance-of-uncertainty/)

""")


            st.download_button(
            f"Download forecast",
            csv,
            f"{target_metric_col} forecast {earliest_date} to {latest_date} - trend at {trend_percent}%.csv",
            f"{target_metric_col} forecast {earliest_date} to {latest_date} - trend at {trend_percent}%/csv",
            key='download-csv'
            )
            

            st.markdown(f"""
-------------
                        
### Something wrong with your forecast?

If your forecast looks weird and you're not sure what to do, there are some things you can try.
                        
- If your forecast is including negative numbers where there shouldn't be negative numbers (i.e. you're forecasting traffic, which is 0 at minimum) try reloading the page and switching on "use log scale" in the column selection section.
                        
- Try including regressors in your forecast data (extra columns which highlight patterns in the historic data). Be aware - to use regressors you'll need to extend your date column into the future and include values in the regressor columns for the blank future rows.

- Try including more historic data to help the model understand past seasonal patterns


""")


if __name__ == "__main__":
    try:
        # Add tracking
        tracking_args_dict: MeasurementArguments = {
            # "testing_mode": True,
            "page_location": "python_trends_adjusting", 
            "page_title": "python trends adjusting", 
            "skip_stage": ["start", "end"]
        }
        main(ga4py_args_remove = tracking_args_dict)
    except Exception as e:
        # Log the full traceback to console or a file
        logging.error("An exception occurred", exc_info=True)

        # Display a user-friendly error message
        st.error(e)