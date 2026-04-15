"""Theme utilities for the Mike Streamlit frontend.

Provides theme colors, CSS generation, and system preference detection
for dark/light mode support.
"""

from __future__ import annotations

from typing import Dict, Any, Optional
import streamlit as st


# Theme color definitions
THEME_COLORS = {
    "dark": {
        "background": "#0e1117",
        "secondary_background": "#262730",
        "text": "#fafafa",
        "text_secondary": "#a0a0a0",
        "primary": "#ff4b4b",
        "primary_hover": "#ff6b6b",
        "success": "#00c851",
        "warning": "#ffbb33",
        "error": "#ff4444",
        "info": "#3498db",
        "border": "#3d3d3d",
        "card_background": "#1e1e1e",
        "chart_background": "#1e1e1e",
        "grid_color": "#2d2d2d",
        "accent_blue": "#3498db",
        "accent_green": "#2ecc71",
        "accent_purple": "#9b59b6",
        "accent_gray": "#95a5a6",
    },
    "light": {
        "background": "#ffffff",
        "secondary_background": "#f0f2f6",
        "text": "#31333f",
        "text_secondary": "#6c757d",
        "primary": "#ff4b4b",
        "primary_hover": "#ff6b6b",
        "success": "#00c851",
        "warning": "#ffbb33",
        "error": "#ff4444",
        "info": "#3498db",
        "border": "#d1d5db",
        "card_background": "#f8f9fa",
        "chart_background": "#ffffff",
        "grid_color": "#e9ecef",
        "accent_blue": "#3498db",
        "accent_green": "#2ecc71",
        "accent_purple": "#9b59b6",
        "accent_gray": "#95a5a6",
    },
}


def get_current_theme() -> str:
    """Get the current theme from session state or settings.

    Returns:
        Current theme name ('dark' or 'light')
    """
    # Check session state first (for runtime toggle)
    if "current_theme" in st.session_state:
        return st.session_state.current_theme

    # Fall back to settings
    if "settings" in st.session_state:
        return st.session_state.settings.get("theme", "dark")

    # Default to dark
    return "dark"


def set_theme(theme: str) -> None:
    """Set the current theme in session state.

    Args:
        theme: Theme name ('dark' or 'light')
    """
    st.session_state.current_theme = theme


def get_theme_colors(theme: Optional[str] = None) -> Dict[str, str]:
    """Get color dictionary for a theme.

    Args:
        theme: Theme name ('dark' or 'light'), defaults to current theme

    Returns:
        Dictionary of color names to hex values
    """
    if theme is None:
        theme = get_current_theme()

    return THEME_COLORS.get(theme, THEME_COLORS["dark"])


def generate_css(theme: Optional[str] = None) -> str:
    """Generate CSS styles for the specified theme.

    Args:
        theme: Theme name ('dark' or 'light'), defaults to current theme

    Returns:
        CSS string for the theme
    """
    colors = get_theme_colors(theme)

    css = f"""
    <style>
    /* Theme: {theme or get_current_theme()} */
    
    /* Main app background */
    .stApp {{
        background-color: {colors["background"]};
    }}
    
    /* Main content area */
    .main {{
        padding: 2rem;
        background-color: {colors["background"]};
    }}
    
    /* Sidebar */
    [data-testid="stSidebar"] {{
        background-color: {colors["secondary_background"]};
        border-right: 1px solid {colors["border"]};
    }}
    
    /* Text colors */
    .stMarkdown, .stText, p, h1, h2, h3, h4, h5, h6 {{
        color: {colors["text"]};
    }}
    
    /* Caption text */
    .stCaption, [data-testid="stCaption"] {{
        color: {colors["text_secondary"]};
    }}
    
    /* Buttons */
    .stButton>button {{
        width: 100%;
        background-color: {colors["primary"]};
        color: #ffffff;
        border: none;
        border-radius: 0.5rem;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }}
    
    .stButton>button:hover {{
        background-color: {colors["primary_hover"]};
        box-shadow: 0 2px 8px rgba(255, 75, 75, 0.4);
    }}
    
    .stButton>button:active {{
        background-color: {colors["primary"]};
    }}
    
    /* Secondary buttons */
    .stButton>button[kind="secondary"] {{
        background-color: {colors["secondary_background"]};
        color: {colors["text"]};
        border: 1px solid {colors["border"]};
    }}
    
    /* Metric cards */
    .metric-card {{
        background-color: {colors["card_background"]};
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
        border: 1px solid {colors["border"]};
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }}
    
    /* Log container */
    .log-container {{
        background-color: {colors["card_background"]};
        color: {colors["text"]};
        padding: 1rem;
        border-radius: 5px;
        font-family: monospace;
        max-height: 400px;
        overflow-y: auto;
        border: 1px solid {colors["border"]};
    }}
    
    /* Expander */
    [data-testid="stExpander"] {{
        background-color: {colors["secondary_background"]};
        border-radius: 8px;
        border: 1px solid {colors["border"]};
    }}
    
    /* Input fields */
    .stTextInput>div>div>input,
    .stTextArea>div>div>textarea {{
        background-color: {colors["secondary_background"]};
        color: {colors["text"]};
        border: 1px solid {colors["border"]};
        border-radius: 4px;
    }}
    
    /* Select boxes */
    .stSelectbox>div>div {{
        background-color: {colors["secondary_background"]};
        color: {colors["text"]};
        border: 1px solid {colors["border"]};
    }}
    
    /* Progress bars */
    .stProgress>div>div>div {{
        background-color: {colors["primary"]};
    }}
    
    /* Data frames */
    .stDataFrame {{
        background-color: {colors["secondary_background"]};
        border-radius: 8px;
        border: 1px solid {colors["border"]};
    }}
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {{
        width: 10px;
        height: 10px;
    }}
    
    ::-webkit-scrollbar-track {{
        background: {colors["secondary_background"]};
        border-radius: 5px;
    }}
    
    ::-webkit-scrollbar-thumb {{
        background: {colors["border"]};
        border-radius: 5px;
    }}
    
    ::-webkit-scrollbar-thumb:hover {{
        background: {colors["text_secondary"]};
    }}
    
    /* Status badges */
    .status-badge {{
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.875rem;
        font-weight: 500;
    }}
    
    .status-success {{
        background-color: {colors["success"]}20;
        color: {colors["success"]};
        border: 1px solid {colors["success"]};
    }}
    
    .status-warning {{
        background-color: {colors["warning"]}20;
        color: {colors["warning"]};
        border: 1px solid {colors["warning"]};
    }}
    
    .status-error {{
        background-color: {colors["error"]}20;
        color: {colors["error"]};
        border: 1px solid {colors["error"]};
    }}
    
    .status-info {{
        background-color: {colors["info"]}20;
        color: {colors["info"]};
        border: 1px solid {colors["info"]};
    }}
    
    /* File tree styling */
    .file-tree-item {{
        color: {colors["text"]};
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        transition: background-color 0.2s;
    }}
    
    .file-tree-item:hover {{
        background-color: {colors["secondary_background"]};
    }}
    
    /* Code blocks */
    .stCodeBlock {{
        background-color: {colors["card_background"]};
        border: 1px solid {colors["border"]};
        border-radius: 8px;
    }}
    
    /* Tabs */
    [data-testid="stTabs"] {{
        background-color: {colors["background"]};
    }}
    
    [data-testid="stTab"] {{
        color: {colors["text_secondary"]};
    }}
    
    [data-testid="stTab"][aria-selected="true"] {{
        color: {colors["primary"]};
        border-bottom: 2px solid {colors["primary"]};
    }}
    
    /* Dividers */
    hr {{
        border-color: {colors["border"]};
        margin: 1.5rem 0;
    }}
    
    /* Success/Warning/Error messages */
    .stSuccess {{
        background-color: {colors["success"]}15;
        border-left: 4px solid {colors["success"]};
        color: {colors["text"]};
    }}
    
    .stWarning {{
        background-color: {colors["warning"]}15;
        border-left: 4px solid {colors["warning"]};
        color: {colors["text"]};
    }}
    
    .stError {{
        background-color: {colors["error"]}15;
        border-left: 4px solid {colors["error"]};
        color: {colors["text"]};
    }}
    
    .stInfo {{
        background-color: {colors["info"]}15;
        border-left: 4px solid {colors["info"]};
        color: {colors["text"]};
    }}
    </style>
    """

    return css


def get_chart_theme(theme: Optional[str] = None) -> Dict[str, Any]:
    """Get Plotly chart theme configuration.

    Args:
        theme: Theme name ('dark' or 'light'), defaults to current theme

    Returns:
        Dictionary of Plotly layout settings
    """
    colors = get_theme_colors(theme)

    return {
        "paper_bgcolor": colors["chart_background"],
        "plot_bgcolor": colors["chart_background"],
        "font": {"color": colors["text"], "family": "Arial, sans-serif"},
        "title": {"font": {"color": colors["text"]}},
        "xaxis": {
            "gridcolor": colors["grid_color"],
            "linecolor": colors["border"],
            "tickfont": {"color": colors["text_secondary"]},
            "title": {"font": {"color": colors["text"]}},
        },
        "yaxis": {
            "gridcolor": colors["grid_color"],
            "linecolor": colors["border"],
            "tickfont": {"color": colors["text_secondary"]},
            "title": {"font": {"color": colors["text"]}},
        },
        "legend": {
            "font": {"color": colors["text"]},
            "bgcolor": colors["secondary_background"],
        },
        "colorway": [
            colors["primary"],
            colors["accent_blue"],
            colors["accent_green"],
            colors["accent_purple"],
            colors["warning"],
            colors["info"],
            colors["accent_gray"],
        ],
    }


def apply_chart_theme(fig, theme: Optional[str] = None):
    """Apply theme to a Plotly figure.

    Args:
        fig: Plotly figure object
        theme: Theme name ('dark' or 'light'), defaults to current theme

    Returns:
        Modified figure with theme applied
    """
    chart_theme = get_chart_theme(theme)

    fig.update_layout(
        paper_bgcolor=chart_theme["paper_bgcolor"],
        plot_bgcolor=chart_theme["plot_bgcolor"],
        font=chart_theme["font"],
        xaxis=chart_theme["xaxis"],
        yaxis=chart_theme["yaxis"],
        legend=chart_theme["legend"],
    )

    return fig


def get_edge_type_colors(theme: Optional[str] = None) -> Dict[str, str]:
    """Get colors for dependency graph edge types.

    Args:
        theme: Theme name ('dark' or 'light'), defaults to current theme

    Returns:
        Dictionary mapping edge types to colors
    """
    colors = get_theme_colors(theme)

    return {
        "import": colors["accent_green"],
        "call": colors["accent_blue"],
        "inheritance": colors["accent_purple"],
        "depends_on": colors["accent_gray"],
    }


def get_log_level_colors(theme: Optional[str] = None) -> Dict[str, str]:
    """Get colors for log levels.

    Args:
        theme: Theme name ('dark' or 'light'), defaults to current theme

    Returns:
        Dictionary mapping log levels to colors
    """
    colors = get_theme_colors(theme)

    return {
        "DEBUG": colors["text_secondary"],
        "INFO": colors["info"],
        "WARNING": colors["warning"],
        "ERROR": colors["error"],
        "SUCCESS": colors["success"],
    }


def render_theme_toggle() -> None:
    """Render a theme toggle button in the sidebar."""
    current_theme = get_current_theme()

    theme_icons = {"dark": "🌙", "light": "☀️"}

    next_theme = "light" if current_theme == "dark" else "dark"
    button_label = f"{theme_icons[next_theme]} Switch to {next_theme.title()} Mode"

    if st.button(button_label, use_container_width=True, key="theme_toggle"):
        set_theme(next_theme)
        st.rerun()


def detect_system_theme() -> str:
    """Detect system theme preference.

    Returns:
        'dark' or 'light' based on system preference

    Note: This is a placeholder as Streamlit cannot directly detect
    system theme. In practice, we use a default or user preference.
    """
    # Streamlit doesn't provide direct system theme detection
    # Return dark as default for now
    return "dark"
