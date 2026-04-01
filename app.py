from pathlib import Path

import streamlit as st
import yaml


def load_settings() -> dict:
    config_path = Path("config/settings.yaml")
    with open(config_path) as f:
        return yaml.safe_load(f)


def main():
    st.set_page_config(
        page_title="Portfolio Intelligence V6.1",
        page_icon="⛏️",
        layout="wide",
    )

    settings = load_settings()

    page = st.sidebar.radio(
        "Navigation",
        ["Daily", "Weekly", "Monthly"],
        index=0,
    )

    if page == "Daily":
        from dashboards.daily import render

        render(settings)
    elif page == "Weekly":
        st.info("Weekly dashboard — coming in milestone 2")
    elif page == "Monthly":
        st.info("Monthly dashboard — coming in milestone 2")


if __name__ == "__main__":
    main()
