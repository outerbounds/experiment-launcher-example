import os
from metaflow import Flow
from obproject import ProjectEvent

def get_parameters(flow_name):
    runs = [run for run in Flow(flow_name) if 'start' in run]
    if runs:
        # fetch parameter names from the latest run
        info = runs[0]['start'].task['_graph_info'].data['parameters']
        param_names = [obj['name'] for obj in info if obj['type'] == 'Parameter']
        for run in runs:
            t = run['start'].task
            yield {
                'run_id': run.id,
                'created_at': run.created_at,
                'parameters': {p: t[p].data for p in param_names}
            }

def trigger_event(event_name, params):
    print('Triggering an experiment with parameters:', params)
    ProjectEvent(
        event_name, project=os.environ["OB_PROJECT"], branch=os.environ["OB_BRANCH"]
    ).publish(params)
