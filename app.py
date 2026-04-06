from pathlib import Path

import streamlit as st
import yaml


def load_settings() -> dict:
    config_path = Path("config/settings.yaml")
    with open(config_path) as f:
        return yaml.safe_load(f)


def main():
    st.set_page_config(
        page_title="Portfolio Intelligence V7",
        page_icon="⛏️",
        layout="wide",
    )

    settings = load_settings()

    # Custom styles
    st.markdown("""
    <style>
        section[data-testid="stSidebar"] {
            background-color: #355070;
        }
        section[data-testid="stSidebar"] * {
            color: white !important;
        }
        /* Hide Streamlit button containers in sidebar */
        section[data-testid="stSidebar"] .stButton {
            display: none;
        }
        /* Main content primary buttons */
        button[kind="primary"] {
            background-color: #355070 !important;
            border-color: #355070 !important;
        }
        div[data-testid="stMetricLabel"] {
            color: #6d597a !important;
        }
        /* Sidebar nav links — must override the * selector */
        section[data-testid="stSidebar"] .sidebar-nav a {
            display: block;
            padding: 8px 16px;
            color: rgba(255,255,255,0.7) !important;
            text-decoration: none;
            font-size: 18px;
        }
        section[data-testid="stSidebar"] .sidebar-nav a:hover {
            color: white !important;
        }
        section[data-testid="stSidebar"] .sidebar-nav a.active {
            color: #eaac8b !important;
            font-weight: 600;
        }
    </style>
    """, unsafe_allow_html=True)

    # Navigation via query params
    pages = ["Daily", "Weekly", "Monthly"]
    current = st.query_params.get("page", "Daily")
    if current not in pages:
        current = "Daily"

    with st.sidebar:
        nav_html = '<div class="sidebar-nav">'
        for p in pages:
            cls = ' class="active"' if p == current else ""
            nav_html += f'<a href="?page={p}"{cls}>{p}</a>'
        nav_html += "</div>"
        st.markdown(nav_html, unsafe_allow_html=True)

    page = current

    if page == "Daily":
        from dashboards.daily import render

        render(settings)
    elif page == "Weekly":
        from dashboards.weekly import render

        render(settings)
    elif page == "Monthly":
        from dashboards.monthly import render

        render(settings)


if __name__ == "__main__":
    main()
