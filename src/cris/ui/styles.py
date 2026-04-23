import streamlit as st


def inject_global_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@400;500;600;700&display=swap');

        :root {
            --bg: #0b0f19;
            --card: linear-gradient(145deg, rgba(22, 28, 45, 0.8) 0%, rgba(13, 17, 28, 0.9) 100%);
            --card-2: rgba(22, 28, 45, 0.6);
            --ink: #e2e8f0;
            --muted: #94a3b8;
            --accent: #3b82f6;
            --accent-2: #8b5cf6;
            --accent-3: #10b981;
            --border: rgba(255, 255, 255, 0.08);
            --glow: 0 4px 6px -1px rgba(0, 0, 0, 0.5), 0 2px 4px -1px rgba(0, 0, 0, 0.3);
        }

        .stApp {
            background: var(--bg);
            color: var(--ink);
        }

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            color: var(--ink);
        }

        h1, h2, h3 {
            font-family: 'Outfit', sans-serif;
            letter-spacing: -0.01em;
            font-weight: 600;
            color: #ffffff;
        }

        p, label, span, div {
            color: var(--ink);
        }

        [data-testid="block-container"] {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }

        [data-testid="stHeader"] {
            background: rgba(0, 0, 0, 0);
        }

        [data-testid="stMetric"], .stDataFrame, .stPlotlyChart, div[data-testid="stMarkdownContainer"], div[data-testid="stFileUploader"] {
            border-radius: 22px;
        }

        [data-testid="stMetric"] {
            background: var(--card);
            border: 1px solid var(--border);
            padding: 1rem;
            box-shadow: var(--glow);
            backdrop-filter: blur(10px);
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(10, 12, 18, 0.98) 0%, rgba(4, 6, 10, 0.98) 100%);
            border-right: 1px solid var(--border);
        }

        [data-testid="stSidebar"] * {
            color: var(--ink) !important;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 0.75rem;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border);
            padding: 0.35rem;
            border-radius: 999px;
        }

        .stTabs [data-baseweb="tab"] {
            background: rgba(255,255,255,0.02);
            border-radius: 999px;
            padding: 0.6rem 1.1rem;
            border: 1px solid var(--border);
            color: var(--ink);
            transition: all 0.2s ease;
        }

        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, rgba(77, 215, 255, 0.18) 0%, rgba(139, 125, 255, 0.18) 100%) !important;
            border: 1px solid rgba(77, 215, 255, 0.35) !important;
            box-shadow: 0 0 20px rgba(77, 215, 255, 0.12);
        }

        .stTabs [data-baseweb="tab"]:hover {
            background: rgba(255, 255, 255, 0.06);
        }

        .stDataFrame, .stPlotlyChart, div[data-testid="stFileUploader"] {
            background: var(--card-2);
            border: 1px solid var(--border);
            box-shadow: var(--glow);
            padding: 0.55rem;
        }

        div[data-testid="stMarkdownContainer"] h3,
        div[data-testid="stMarkdownContainer"] h2,
        div[data-testid="stMarkdownContainer"] h1 {
            color: #ffffff;
        }

        div[data-testid="stFileUploader"] section {
            background: transparent;
            color: var(--ink);
        }

        .stProgress > div > div > div > div {
            background: linear-gradient(90deg, var(--accent) 0%, var(--accent-2) 50%, var(--accent-3) 100%);
        }

        .stAlert {
            background: rgba(255, 255, 255, 0.04);
            color: var(--ink);
            border: 1px solid var(--border);
            border-radius: 18px;
        }

        .stSelectbox label, .stMultiSelect label, .stTextInput label {
            color: var(--ink) !important;
        }

        div[data-baseweb="select"] > div {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border);
            color: var(--ink);
        }

        code {
            color: #d7f6ff;
            background: rgba(77, 215, 255, 0.08);
            border-radius: 8px;
            padding: 0.15rem 0.35rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
