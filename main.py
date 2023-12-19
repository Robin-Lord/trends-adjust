import streamlit as st
import st_helpers as sth
import pandas as pd
import process_forecast as pf
import pandas_helpers as pdh
import seaborn as sns #type: ignore
import charting_helpers as ch
import datetime as datetime

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
    else:
        st.write(f"Uploaded file: {st.session_state.uploaded_file}")

def handle_uploaded_file():
        # Reset upload section
    if st.session_state.step == "upload":
        st.session_state.step = "columns"
        st.session_state.file_data = pd.read_csv(st.session_state.uploaded_file)
        st.experimental_rerun()

    # Read and display the data
    data = st.session_state.file_data
    st.write("Example top and bottom rows of your CSV:")
    st.write(data.head())
    st.write("...")
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
        st.session_state.date_col = st.selectbox("""                          
    Select the Date column (by default will select any column called 'Date'):""", 
        options=data.columns, index=date_col_index)
        date_col = st.session_state.date_col

        # Selection for Target Metric column
        st.session_state.target_metric_col = st.selectbox("Select the Target Metric column:", 
                                        options=target_metrics_options, 
                                        index= target_metric_col_index)
        target_metric_col = st.session_state.target_metric_col

        # Selection for Regressor columns
        st.session_state.regressor_col_list = st.multiselect("Select Regressor columns:", 
                                        options=regressor_options,
                                        default=default_regressor_cols)
        regressor_cols = st.session_state.regressor_col_list

        # Force state update to flush through change 
        # (streamlit seems to need a second) update
        if (
            st.session_state.date_col != default_date_col
            or 
            st.session_state.target_metric_col != default_target_metric_col
            or st.session_state.regressor_col_list != default_regressor_cols
            ):
            st.experimental_rerun()


        # Display chosen categories
        st.write("You categorized the columns as follows:")
        st.write(f"Date column: {date_col}")
        st.write(f"Target Metric column: {target_metric_col}")
        st.write(f"Regressor columns: {', '.join(regressor_cols) if regressor_cols else 'None'}")

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



def main():


    add_custom_css()

    st.title("Forecast with adjustable trend")

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
        st.session_state.regressor_col_list = []


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

            # Make prediction
            st.session_state.prophet_forecast = pf.create_forecast(
                        fitted_model = st.session_state.prophet_model,
                        future_data = future_data
                        )
        
        prophet_forecast = st.session_state.prophet_forecast


        forecast_expander = st.expander(label = "Run forecast", expanded=st.session_state.step == "forecast")

        # Calculate the granularity options

        with forecast_expander:

            # Adjust prediction
            trend_adjustment = st.slider(
                label = "trend adjustment",
                min_value = 0.0,
                max_value = 1.0,
                value = 1.0,
                step = 0.05
                )
            
            
            adjusted_forecast = pf.reverse_engineer_forecast_for_trend(
                forecast_df = prophet_forecast,
                multiplier = trend_adjustment,
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

            st.write("Choose dates to filter the chart below (this won't change your data)")

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
                    min_value=first_date_to_show,
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


            if last_date_to_show<=first_date_to_show:
                if first_date_to_show == latest_date:
                    first_date_to_show = first_date_to_show-datetime.timedelta(days = 2)
                # Make sure users can't accidentally over-filter table
                last_date_to_show = first_date_to_show+datetime.timedelta(days=1)

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

            trend_percent = int((trend_adjustment/1)*100)

            st.write(f"Click download to download your forecast, assuming trend is applied at {trend_percent}% strength")

            st.download_button(
            f"Download forecast",
            csv,
            f"{target_metric_col} forecast {earliest_date} to {latest_date} - trend at {trend_percent}%.csv",
            f"{target_metric_col} forecast {earliest_date} to {latest_date} - trend at {trend_percent}%/csv",
            key='download-csv'
            )
            



if __name__ == "__main__":
    main()
