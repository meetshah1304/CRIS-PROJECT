import streamlit as st
from pathlib import Path

def apply_custom_theme():
    st.set_page_config(
        page_title="CRIS | Intelligence System",
        page_icon="⚖️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    css_path = Path(__file__).parent / "style.css"
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()
            st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
