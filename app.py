# --- TSEG Branded Attorney Bio Scraper (Streamlit) ---
import time, re
import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

# -----------------------------
# Branding / Theme
# -----------------------------
TSEG_LOGO = "https://www.tseg.com/wp-content/uploads/2023/02/tseg-social-thumbnail.png"
ACCENT = "#9ccb3b"  # TSEG green

st.set_page_config(
    page_title="TSEG • Attorney Bio Scraper",
    page_icon=TSEG_LOGO,
    layout="wide",
)

# Custom CSS
st.markdown(
    f"""
    <style>
      .tseg-header {{
        text-align:center;
        padding:18px;
        border-radius:16px;
        background: linear-gradient(135deg, {ACCENT}22, rgba(255,255,255,0.04));
        border: 1px solid {ACCENT}55;
        margin-bottom: 20px;
      }}
      .tseg-header h1 {{
        font-weight: 800; 
        font-size: 1.8rem; 
        margin: 0;
      }}
      .tseg-sub {{
        font-size: 0.95rem;
        color: rgba(255,255,255,0.75);
        margin-top: 6px;
      }}
      .tseg-logo {{
        display:block;
        margin-left:auto; margin-right:auto;
        margin-bottom:14px;
      }}
      .stButton>button {{
        border-radius: 12px; 
        border:1px solid {ACCENT}55;
        padding: 10px 14px; 
        font-weight: 600;
        color: white;
        background-color: {ACCENT}33;
      }}
      .stButton>button:hover {{
        border-color: {ACCENT};
        background-color: {ACCENT}55;
      }}
      .stDataFrame div[data-testid="stDataFrame"] {{
        border-radius: 12px; 
        overflow:hidden;
      }}
    </style>
    """,
    unsafe_allow_html=True,
)

# Header block
st.markdown(
    f"""
    <div class="tseg-header">
      <img src="{TSEG_LOGO}" width="110" class="tseg-logo"/>
      <h1>Attorney Bio Scraper — Conference Edition</h1>
      <div class="tseg-sub">
        Surface quick talking points from attorney biography pages (education, hobbies, pets, family, community).
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
