"""Sedimentation basin design for CE 323 (Streamlit app entry point)."""
import streamlit as st

st.set_page_config(
    page_title="Sedimentation Basin Design · CE 323",
    page_icon=":material/water:",
    layout="wide",
    initial_sidebar_state="auto",
)

import pages_basin  # noqa: E402  (after set_page_config)

st.navigation(
    [
        st.Page(pages_basin.tool_page, title="Basin design", icon=":material/straighten:", default=True),
        st.Page(pages_basin.accessibility_page, title="Accessibility", icon=":material/accessibility_new:",
                url_path="accessibility"),
    ]
).run()
