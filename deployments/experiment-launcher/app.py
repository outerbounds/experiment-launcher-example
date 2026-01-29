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
            "run_id": entry["run_id"],
            "created_at": formatted_ts,
        }
        row.update(entry["parameters"])
        rows.append(row)
    return rows

rows = load_runs()

if not rows:
    st.warning("No runs found.")
    st.stop()

df = pd.DataFrame(rows)
param_columns = [c for c in df.columns if c not in ("run_id", "created_at")]

# Initialize selected parameters in session state
if "selected_params" not in st.session_state:
    st.session_state.selected_params = {}

def toggle_cell(param, row_idx, value):
    current = st.session_state.selected_params.get(param)
    if current and current["row"] == row_idx:
        del st.session_state.selected_params[param]
    else:
        st.session_state.selected_params[param] = {"row": row_idx, "value": value}

# --- Layout ---
table_col, panel_col = st.columns([3, 2])

with table_col:
    st.subheader("Past Runs")

    # Header
    header_cols = st.columns([2, 2] + [1] * len(param_columns))
    header_cols[0].markdown("**Run ID**")
    header_cols[1].markdown("**Created At**")
    for i, p in enumerate(param_columns):
        header_cols[i + 2].markdown(f"**{p}**")

    st.divider()

    for row_idx, row in df.iterrows():
        cols = st.columns([2, 2] + [1] * len(param_columns))
        cols[0].text(row["run_id"])
        cols[1].text(row["created_at"])
        for i, p in enumerate(param_columns):
            val = row[p]
            key = f"cell_{row_idx}_{p}"
            is_selected = (
                st.session_state.selected_params.get(p, {}).get("row") == row_idx
            )
            btn_type = "primary" if is_selected else "secondary"
            cols[i + 2].button(
                str(val),
                key=key,
                type=btn_type,
                on_click=toggle_cell,
                args=(p, row_idx, val),
                use_container_width=True,
            )

with panel_col:
    st.subheader("Experiment Parameters")

    if not st.session_state.selected_params:
        st.info("Select parameter values from the table on the left.")
    else:
        edited_params = {}
        for p in param_columns:
            if p not in st.session_state.selected_params:
                continue
            val = st.session_state.selected_params[p]["value"]
            # Render an appropriate input based on value type
            if isinstance(val, bool):
                edited_params[p] = st.checkbox(p, value=val, key=f"edit_{p}")
            elif isinstance(val, int):
                edited_params[p] = st.number_input(p, value=val, step=1, key=f"edit_{p}")
            elif isinstance(val, float):
                edited_params[p] = st.number_input(p, value=val, key=f"edit_{p}")
            else:
                edited_params[p] = st.text_input(p, value=str(val), key=f"edit_{p}")

        st.divider()

        if st.button("Launch Experiment", type="primary", use_container_width=True):
            if not edited_params:
                st.error("Select at least one parameter.")
            else:
                try:
                    trigger_event(EVENT_NAME, edited_params)
                    st.success(f"Experiment launched with: {edited_params}")
                except Exception as e:
                    st.error(f"Failed to launch: {e}")
