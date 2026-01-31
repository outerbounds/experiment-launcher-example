import streamlit as st
import pandas as pd
from datetime import datetime
from util import get_parameters, list_branches, trigger_event


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
/* Pagination buttons: smaller, outlined style */
.pagination-controls button {
    font-size: 0.75rem !important;
    padding: 0.15rem 0.8rem !important;
    border-radius: 1rem !important;
    min-height: 0 !important;
    height: auto !important;
}
.pagination-controls p, .pagination-controls span {
    font-size: 0.8rem !important;
    color: #888 !important;
}
</style>
""", unsafe_allow_html=True)

# --- Flow / Project / Branch selection ---
query = st.query_params

flow_name = query.get("flow", "")
flow_name = st.text_input("Flow name", value=flow_name)

if flow_name:
    st.query_params["flow"] = flow_name

if not flow_name:
    st.info("Enter a flow name to continue.")
    st.stop()

@st.cache_data(ttl=60)
def load_branches(flow_name):
    return {proj: sorted(branches) for proj, branches in list_branches(flow_name).items()}

try:
    projects = load_branches(flow_name)
except Exception as e:
    st.error(f"Could not load flow **{flow_name}**: {e}")
    st.stop()

if not projects:
    st.error(f"No projects found for flow **{flow_name}**.")
    st.stop()

project_names = sorted(projects.keys())
default_project = query.get("project", "")
project_idx = project_names.index(default_project) if default_project in project_names else 0
selected_project = st.selectbox("Project", project_names, index=project_idx)
st.query_params["project"] = selected_project

branches = projects[selected_project]  # list of (pretty_branch, metaflow_branch)
pretty_branches = [b[0] for b in branches]
default_branch = query.get("branch", "")
branch_idx = pretty_branches.index(default_branch) if default_branch in pretty_branches else 0
selected_branch_idx = st.selectbox("Branch", range(len(branches)), index=branch_idx,
                                   format_func=lambda i: pretty_branches[i])
selected_pretty, selected_metaflow = branches[selected_branch_idx]
st.query_params["branch"] = selected_pretty

st.divider()

# --- Load run data ---
@st.cache_data(ttl=60)
def load_runs(flow_name, project, metaflow_branch):
    rows = []
    for entry in get_parameters(flow_name, project, metaflow_branch):
        ts = entry["created_at"]
        if isinstance(ts, datetime):
            formatted_ts = ts.strftime("%Y-%m-%d %H:%M:%S")
        else:
            formatted_ts = str(ts).split(".")[0]
        row = {
            "run": f"{entry['run_id']} ({formatted_ts})",
            "event_name": entry["event_name"],
        }
        row.update(entry["parameters"])
        rows.append(row)
    return rows

rows = load_runs(flow_name, selected_project, selected_metaflow)

if not rows:
    st.warning("No runs found.")
    st.stop()

df = pd.DataFrame(rows)
event_name = df["event_name"].iloc[0]
param_columns = [c for c in df.columns if c not in ("run", "event_name")]

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

    # Pagination
    PAGE_SIZE = 10
    total_runs = len(df)
    total_pages = (total_runs + PAGE_SIZE - 1) // PAGE_SIZE
    if "run_page" not in st.session_state:
        st.session_state.run_page = 0
    page = st.session_state.run_page
    page_start = page * PAGE_SIZE
    page_end = min(page_start + PAGE_SIZE, total_runs)
    page_df = df.iloc[page_start:page_end]

    for row_idx, row in page_df.iterrows():
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

    # Pagination controls
    if total_pages > 1:
        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
        st.divider()
        with st.container():
            st.markdown('<div class="pagination-controls">', unsafe_allow_html=True)
            prev_col, info_col, next_col = st.columns([1, 2, 1])
            with prev_col:
                if page > 0:
                    st.button("← Prev", on_click=lambda: setattr(st.session_state, 'run_page', st.session_state.run_page - 1))
            with info_col:
                st.markdown(f"<div style='text-align:center; padding-top:0.3rem; font-size:0.8rem; color:#888;'>Page {page + 1} of {total_pages} &nbsp;·&nbsp; {page_start + 1}–{page_end} of {total_runs} runs</div>", unsafe_allow_html=True)
            with next_col:
                if page < total_pages - 1:
                    st.button("Next →", on_click=lambda: setattr(st.session_state, 'run_page', st.session_state.run_page + 1))
            st.markdown('</div>', unsafe_allow_html=True)

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
            trigger_event(event_name, edited_params)
            st.success(f"Experiment launched with: {edited_params}")
        except Exception as e:
            st.error(f"Failed to launch: {e}")
