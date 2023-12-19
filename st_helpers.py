import streamlit as st
import os

def update_step_state(
        previous_step: str,
        new_step: str
    ):
    if st.session_state.step == previous_step:
        st.session_state.step = new_step
        st.experimental_rerun()

def continue_or_reset(message = ""):
    # Auto testing flag that lets us choose these choices
    auto_yes_no = os.getenv("AUTO_YES_NO")

    # Yes/No buttons
    st.write(message)
    if st.button('Yes') or auto_yes_no == "yes":
        st.write('You selected "Yes" - continuing.')
        return True
    elif st.button('No') or auto_yes_no == "no":
        raise ValueError("You selected 'no' meaning you don't want to continue - please refresh the page")
    

@st.experimental_memo
def convert_df(df):
   return df.to_csv(index=False).encode('utf-8')

