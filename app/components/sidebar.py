import streamlit as st
import os


def sidebar():
    with st.sidebar:
        st.image("https://th.bing.com/th/id/OIP.WzdKBeSaMugMpnbLJL7KWwHaE8?pid=ImgDet&rs=1")

        st.markdown("---")
        st.markdown("# About")
        st.markdown("""
            GPT Smart Search allows you to ask questions about your
            documents and get accurate answers with instant citations.
            
            This engine finds information from the following:
            - Snowflake-BasicOverview.pdf
            - Snowflake-Internals.pdf
            - Snowflake-Security-Guide.pdf
           
        """
        )
        st.markdown("---")
