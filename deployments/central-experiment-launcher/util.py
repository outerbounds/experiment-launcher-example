import os
import re
from collections import defaultdict

from metaflow import Flow, get_namespace, namespace
from metaflow.integrations import ArgoEvent
from obproject import ProjectEvent


def list_branches(flow_name):
    namespace(None)
    projects = defaultdict(set)
    for run in Flow(flow_name):
        if "start" in run:
            branch = [
                t.split(":", 1)[1] for t in run.tags if t.startswith("project_branch:")
            ]
            project = [t.split(":", 1)[1] for t in run.tags if t.startswith("project:")]
            if project and branch:
                [metaflow_branch] = branch
                if not metaflow_branch.startswith("user."):
                    if metaflow_branch == "prod":
                        pretty_branch = "main"
                    elif metaflow_branch.startswith("test."):
                        pretty_branch = metaflow_branch[5:]
                    else:
                        pretty_branch = metaflow_branch
                    projects[project[0]].add((pretty_branch, metaflow_branch))
    return projects


def get_parameters(flow_name, project, metaflow_branch):
    # find past runs in this project and branch
    tags = [f"project_branch:{metaflow_branch}", f"project:{project}"]
    namespace(None)
    runs = [
        run
        for run in Flow(flow_name).runs(*tags)
        if "start" in run and "_graph_info" in run["start"].task
    ]
    if runs:
        # fetch parameter names from the latest run
        info = runs[0]["start"].task["_graph_info"].data["parameters"]
        param_names = [obj["name"] for obj in info if obj["type"] == "Parameter"]
        for run in runs:
            t = run["start"].task
            decos = t["_graph_info"].data.get("decorators", [])
            event_name = [
                d["attributes"]["event"] for d in decos if d["name"] == "trigger"
            ]
            if event_name:
                yield {
                    "run_id": run.id,
                    "created_at": run.created_at,
                    "parameters": {p: t[p].data for p in param_names},
                    "event_name": event_name[0],
                }


def trigger_event(event_name, params):
    print("Triggering an experiment with parameters:", params)
    ArgoEvent(event_name).publish(params)
