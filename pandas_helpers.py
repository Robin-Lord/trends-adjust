import streamlit as st
import st_helpers as sth
import pandas as pd
import numpy as np
import process_forecast as pf
from typing import Tuple
from prophet import Prophet # type: ignore


def check_columns(df):
    """
    Function to check if all of the column names are unique
    """


    df_cols = df.columns

    if len(df_cols) != len(list(set(df_cols))):
        # If the deduped list doesn't match the 
        # non-deduped list some of the column names
        # are identical and that will cause problems
        raise ValueError("""
                         
Sorry - it looks like you've uploaded data which has duplicate column
names, please check your csv, make sure each column has a unique name
then refresh the page and try again. Thanks!                         
                         
""")


def date_col_conversion(
        df: pd.DataFrame, 
        date_col: str
        )-> pd.DataFrame:

    try:
        df["raw_date"] = pd.to_datetime(df[date_col], format="%Y-%m-%d")
        df = df.rename(columns={date_col:"ds"}, inplace = False)
    except Exception as e:
        raise ValueError(f"There was a problem with reading your date column ({date_col}) - please make sure you've selected the right one, and that all the dates are in YYYY-MM-DD format")
    
    return df


def check_for_data_blocks(
        row,
        target_column: str,
        date_column: str,
        list_of_empties: list,
        regressor_column_list: list[str],
    ):
    """
    check_for_data_blocks 

    This function uses the mutable nature of a list so
    we can loop through every row in a dataframe and count
    the number of blanks but ALSO do some checks, i.e.
    
    - Make sure that there aren't gaps 
        (essentially we should see ONLY filled 
        rows until the first empty row, and then we 
        should see ONLY empty rows from then until the end). 
    - Check if there are at least a few empty 'target_column' 
        rows at the end of our data, if so that's our forecast
        window, if not we assume we have to generate the forecast window
    - Check if there are any regressor columns with empty spaces
        if so that'll cause Prophet to fail so we need to give a 
        clear and direct error message now so people know what to fix
    - Check if there are any empty cells in the date column
        if so that'll cause Prophet to fail so again we need a 
        clear and direct error message

    Args:
        row (DataFrame row): the row of the dataframe we're checking
        target_column (str): the name of the column we're checking
        date_column (str): the name of the column we'll record in the empty rows list
        list_of_empties (list): a list of dates for the empty rows
        regressor_column_list (list[str]): list of regressor columns to check to make sure they're not N/A
    """



    # Check if the date column is unexpectedly blank
    if pd.isna(row[date_column]) or row[date_column]=="":
        raise ValueError(f"""

It looks like you have a row which has data in it but doesn't have a value
in the date column ({date_column}). Try checking row {row.name} and make sure
the date column is filled (and check the rest of the date column while you're at it!)                         

Then refresh this page and try uploading your data again.
                         
""")

    date_value = row[date_column]


    # check if any of the regressor columns are unexpectedly blank
    for c in regressor_column_list:
        if pd.isna(row[c]) or row[c]=="":
            raise ValueError(f"""
When you're using regressor columns - you have to put a value in every single row
for the regressors. In the row for {date_value} your regressor column {c} is empty. 
Other rows and columns might have the same issue so please check your data, refresh this page
and try again.""")

    value = row[target_column]
    if value == "" or pd.isna(value):
        list_of_empties.append(date_value)
    
    else:
        # Check we haven't had any empties before now
        if len(list_of_empties)> 0:
            raise ValueError(f"""
                             
You have gaps in your data - when we checked your data, column: {target_column}
has an entry for date {date_value} but is missing values for {len(list_of_empties)} 
preceding dates. Here are {min(10,len(list_of_empties))} examples of dates with missing data:
{list_of_empties[:10]}.

To avoid errors - fix your data (so you have a value in your target column for every
historic date, and an empty row for every date you want to forecast), reload this page
and reupload your data.

""")


def check_ordering(
        df: pd.DataFrame, 
        date_col: str) -> Tuple[pd.DataFrame, bool]:
    

    should_continue = True # Default assumption is no issues
    
    # Check the dataframe is ordered correctly
    date_ordered = df[date_col].is_monotonic_increasing

    if not date_ordered:
        should_continue = sth.continue_or_reset("""
The data you uploaded isn't in date order. Do you want to continue?
                              
If you click 'yes' we'll automatically reorder your data for you. 

If you want to start again - reload the page.

""")    
        if should_continue:
            df = df.sort_values(date_col).reset_index().drop(columns=["index"])

    return df, should_continue

def check_and_convert_data(
        df: pd.DataFrame, 
        date_col: str, 
        target_col: str,
        regressor_cols: list
        ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:


    # First convert date column and create expected ds column
    df = date_col_conversion(df = df, date_col = date_col)


    # Then check ordering
    df, ordering_should_continue = check_ordering(
        df=df,
        date_col=date_col)
    

    # Only do the rest of this if we should continue
    if not ordering_should_continue:
        return df, df, df # Just returning data, but we shouldn't use it


    # Create expected "y" column
    if target_col!= "y":
        df = df.rename(columns={target_col:"y"})

    new_target_col = "y"
    new_date_col = "raw_date"

    # Check that there are some rows in the uploaded data to
    # make room for a forecast
    list_of_empty_dates: list = []

    df.apply(lambda x: check_for_data_blocks(
        row = x,
        target_column = new_target_col,
        date_column = new_date_col,
        list_of_empties = list_of_empty_dates,
        regressor_column_list=regressor_cols
        ), axis = 1)
    
    if len(list_of_empty_dates) > 0:
        current: pd.DataFrame = df[~df[new_date_col].isin(list_of_empty_dates)]
        future: pd.DataFrame = df[df[new_date_col].isin(list_of_empty_dates)]
        current_plus_future: pd.DataFrame = df
    
    else:
        # If we have no empty rows we can guess how far in the future
        # we want to forecast BUT that will mean that our regressor
        # columns stop (which is no good) so if the user is trying
        # to use regressors they have to leave empty rows

        if len(regressor_cols) >0:
            raise ValueError(f"""

You have listed regressor columns ({regressor_cols}).

But the column you want to forecast ({target_col}) has an entry for every date.

If you are going to use regressor columns you have to create a row for every date you
want to forecast. The date and regressor columns have to be filled for those rows
and the target column ({target_col}) has to be blank.

That's because regressors are used to influence the forecast, but if they stop on the
same date that the target column does, they won't do anything!

Please reload and either skip using the regressor columns, or add in the extra rows to your data.

""")
        
        # If we're not using regressor columns, we can just generate the dates.
        current = df

        last_date = current[new_date_col].iloc[-1]

        new_dates = pd.date_range(
            start=last_date + pd.Timedelta(days=1), 
            periods=1096, freq='D')
        
        future = pd.DataFrame({
            "ds": new_dates,
            "y": np.nan
        })

        current_plus_future = pd.concat([current, future])
        


    # Once we've done all the checks - change the session variable
    st.session_state.data_checked = True

    return current, future, current_plus_future

def choose_columns(
        df: pd.DataFrame,
        ) -> Tuple[str, int, list[str], str, int, list[str], list[str]]:
    

    default_date_col:str
    default_date_col_index: int
    target_metric_options:list[str]
    default_target_col:str
    default_target_col_index: int
    regressor_options:list[str]
    default_regressors: list[str]

    # Select date column
    if st.session_state.date_col != None:
        default_date_col = st.session_state.date_col
    else:
        default_date_col = next((col for col in df.columns if col.lower() == 'date'), df.columns[0])

    default_date_col_index = df.columns.get_loc(default_date_col)
    
    # Prepare options for Target Metric column, excluding the Date column
    target_metric_options = [col for col in df.columns if col != default_date_col]

    print(f"Target metric options: {target_metric_options}")


    if st.session_state.target_metric_col != None and st.session_state.target_metric_col!=default_date_col:
        default_target_col = st.session_state.target_metric_col
    elif "y" in target_metric_options and default_date_col!="y":
        default_target_col = "y"
    elif "target" in target_metric_options and default_date_col!="target":
        default_target_col = "target"
    else:
        default_target_col = target_metric_options[0]

    default_target_col_index = target_metric_options.index(default_target_col)


    # Prepare options for regressor columns, excluding the other two options
    regressor_options = [col for col in target_metric_options if col != default_target_col]

    if st.session_state.regressor_col_list != None:
        default_regressors = [
            col for 
            col in 
            st.session_state.regressor_col_list
            if col in regressor_options]
    else:
        default_regressors = [col for col in regressor_options if "regressor" in col]

    
    
    return (
        default_date_col, 
        default_date_col_index,
        target_metric_options, 
        default_target_col, 
        default_target_col_index,
        regressor_options,
        default_regressors
        )