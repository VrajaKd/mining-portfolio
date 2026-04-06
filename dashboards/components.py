"""Custom styled components using the project color palette."""

import streamlit as st

# Palette
DUSK_BLUE = "#355070"
DUSTY_LAVENDER = "#6d597a"
SAGE_GREEN = "#6b8f71"
ROSEWOOD = "#b56576"
LIGHT_CORAL = "#e56b6f"
LIGHT_BRONZE = "#eaac8b"

_STYLES = {
    "info": {
        "bg": "#d8d0df",
        "border": DUSTY_LAVENDER,
        "text": DUSK_BLUE,
    },
    "success": {
        "bg": "#d4e6d6",
        "border": SAGE_GREEN,
        "text": DUSK_BLUE,
    },
    "warning": {
        "bg": "#f0cdb8",
        "border": ROSEWOOD,
        "text": DUSK_BLUE,
    },
    "error": {
        "bg": "#fae8e9",
        "border": LIGHT_CORAL,
        "text": DUSK_BLUE,
    },
}


def _alert(message: str, kind: str) -> None:
    s = _STYLES.get(kind, _STYLES["info"])
    st.markdown(
        f"""<div style="
            background-color: {s['bg']};
            border-left: 4px solid {s['border']};
            color: {s['text']};
            padding: 12px 16px;
            border-radius: 4px;
            margin-bottom: 8px;
        ">{message}</div>""",
        unsafe_allow_html=True,
    )


def alert_info(message: str) -> None:
    _alert(message, "info")


def alert_success(message: str) -> None:
    _alert(message, "success")


def alert_warning(message: str) -> None:
    _alert(message, "warning")


def alert_error(message: str) -> None:
    _alert(message, "error")
