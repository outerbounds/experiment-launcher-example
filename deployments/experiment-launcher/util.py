import os
import re
from metaflow import Flow, get_namespace, namespace
from obproject import ProjectEvent


def project_tags():
    if "OB_PROJECT" in os.environ:
        project = os.environ["OB_PROJECT"]
        ob_branch = os.environ["OB_BRANCH"]
        branch = (
            "prod"
            if ob_branch in ("master", "main")
            else re.sub(r"[-/]", "_", ob_branch).lower()
        )
        return [f"project_branch:{branch}", f"project:{project}"]
    else:
        return [get_namespace()]


def get_parameters(flow_name):
    # find past runs in this project and branch
    tags = project_tags()
    namespace(None)
    runs = [run for run in Flow(flow_name).runs(*tags) if "start" in run]
    if runs:
        # fetch parameter names from the latest run
        info = runs[0]["start"].task["_graph_info"].data["parameters"]
        param_names = [obj["name"] for obj in info if obj["type"] == "Parameter"]
        for run in runs:
            t = run["start"].task
            yield {
                "run_id": run.id,
                "created_at": run.created_at,
                "parameters": {p: t[p].data for p in param_names},
            }


def trigger_event(event_name, params):
    print("Triggering an experiment with parameters:", params)
    ProjectEvent(
        event_name, project=os.environ["OB_PROJECT"], branch=os.environ["OB_BRANCH"]
    ).publish(params)
