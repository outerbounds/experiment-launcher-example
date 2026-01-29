import streamlit as st
import pandas as pd
from datetime import datetime
from util import get_parameters, trigger_event

FLOW_NAME = "CascadingParameters"
EVENT_NAME = "launch_experiment"

st.set_page_config(page_title="Experiment Launcher", layout="wide")
st.title("Experiment Launcher")

# Style for selected cells
st.markdown("""
<style>
div[data-testid="stButton"] > button.selected-cell {
    background-color: #4CAF50 !important;
    color: white !important;
    border-color: #4CAF50 !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:first-child p,
[data-testid="stVerticalBlockBorderWrapper"]:first-child span,
[data-testid="stVerticalBlockBorderWrapper"]:first-child button {
    font-size: 0.8rem !important;
}
</style>
""", unsafe_allow_html=True)

# Load run data
@st.cache_data(ttl=60)
def load_runs():
    rows = []
    for entry in get_parameters(FLOW_NAME):
        ts = entry["created_at"]
        if isinstance(ts, datetime):
            formatted_ts = ts.strftime("%Y-%m-%d %H:%M:%S")
        else:
            formatted_ts = str(ts).split(".")[0]
        row = {
            "run": f"{entry['run_id']} ({formatted_ts})",
        }
        row.update(entry["parameters"])
        rows.append(row)
    return rows

rows = load_runs()

if not rows:
    st.warning("No runs found.")
    st.stop()

df = pd.DataFrame(rows)
param_columns = [c for c in df.columns if c != "run"]

def _param_defaults(p):
    sample = df[p].dropna().iloc[0] if not df[p].dropna().empty else ""
    if hasattr(sample, 'item'):
        sample = sample.item()
    if isinstance(sample, bool):
        return ("bool", False)
    elif isinstance(sample, int):
        return ("int", 0)
    elif isinstance(sample, float):
        return ("float", 0.0)
    else:
        return ("str", "")

# Initialize selected parameters in session state
if "selected_params" not in st.session_state:
    st.session_state.selected_params = {}

def toggle_cell(param, row_idx, value):
    current = st.session_state.selected_params.get(param)
    if current and current["row"] == row_idx:
        del st.session_state.selected_params[param]
        # Reset the widget to its default value
        dtype, default_val = _param_defaults(param)
        st.session_state[f"edit_{param}"] = default_val
    else:
        st.session_state.selected_params[param] = {"row": row_idx, "value": value}
        # Update the widget's session state so it reflects the selected value
        # Convert numpy types to native Python types for Streamlit widgets
        if hasattr(value, 'item'):
            value = value.item()
        st.session_state[f"edit_{param}"] = value

# --- Layout ---
table_col, panel_col = st.columns([5, 1])

with table_col:
    st.subheader("Past Runs")

    # Header
    header_cols = st.columns([2] + [1] * len(param_columns))
    header_cols[0].markdown("**Run**")
    for i, p in enumerate(param_columns):
        header_cols[i + 1].markdown(f"**{p}**")

    st.divider()

    for row_idx, row in df.iterrows():
        cols = st.columns([2] + [1] * len(param_columns))
        cols[0].text(row["run"])
        for i, p in enumerate(param_columns):
            val = row[p]
            key = f"cell_{row_idx}_{p}"
            is_selected = (
                st.session_state.selected_params.get(p, {}).get("row") == row_idx
            )
            btn_type = "primary" if is_selected else "secondary"
            cols[i + 1].button(
                str(val),
                key=key,
                type=btn_type,
                on_click=toggle_cell,
                args=(p, row_idx, val),
                use_container_width=True,
            )

with panel_col:
    st.subheader("Experiment Parameters")

    param_defaults = {p: _param_defaults(p) for p in param_columns}

    # Initialize widget session state keys (only on first run)
    for p in param_columns:
        widget_key = f"edit_{p}"
        if widget_key not in st.session_state:
            dtype, default_val = param_defaults[p]
            st.session_state[widget_key] = default_val

    edited_params = {}
    for p in param_columns:
        dtype, default_val = param_defaults[p]

        if dtype == "bool":
            edited_params[p] = st.checkbox(p, key=f"edit_{p}")
        elif dtype == "int":
            edited_params[p] = st.number_input(p, step=1, key=f"edit_{p}")
        elif dtype == "float":
            edited_params[p] = st.number_input(p, key=f"edit_{p}")
        else:
            edited_params[p] = st.text_input(p, key=f"edit_{p}")

    st.divider()

    if st.button("Launch Experiment", type="primary", use_container_width=True):
        try:
            trigger_event(EVENT_NAME, edited_params)
            st.success(f"Experiment launched with: {edited_params}")
        except Exception as e:
            st.error(f"Failed to launch: {e}")
