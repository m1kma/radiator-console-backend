import boto3
import json
import os
from botocore.vendored import requests
from datetime import date,datetime, timedelta

metrics= [{'name': 'Vikke EC2 CPU Utilization',
            'request': {'Namespace':'AWS/EC2',
                        'MetricName':'CPUUtilization',
                        'Dimensions': [{'Name':'AutoScalingGroupName','Value':'vikke-config-cluster-ECSAutoScalingGroup-L6XUH33SPOIL'}],
                        'StartTime': datetime.utcnow() - timedelta(minutes=10),
                        'EndTime': datetime.now(),
                        'Period': 600,
                        'Statistics':['Average'],
                        'Unit':'Percent'},
            'statistics': 'Average',
            'unit': 'Percent'
        },
         {'name': 'RDS CPU Utilization',
            'request': {'Namespace':'AWS/RDS',
                         'MetricName':'CPUUtilization',
                         'StartTime': datetime.utcnow() - timedelta(minutes=10),
                         'EndTime': datetime.now() ,
                         'Period': 600,
                         'Statistics':['Average'],
                         'Unit':'Percent'},
            'statistics': 'Average',
            'unit': 'Percent'}]

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))


def status(event, context):

    pipelines_list = get_pipelines()
    alarms_list = get_alarms()

    if is_gitlab_api_tester_failed():
        alarms_list.append('GitlabAPITester')

    result = {
        "alarms_list" : alarms_list,
        "alarms_raised" : has_alarms(alarms_list),
        "alarms_raised_history" : has_history_alarms(get_alarms_history()),
        "pipelines_running" : is_pipe_running(pipelines_list),
        "pipelines_running_list" : get_running_pipe_list(pipelines_list),
        "pipelines_failed" : is_pipe_failed(pipelines_list),
        "pipelines_failed_list" : get_failed_pipe_list(pipelines_list)
    }

    return {"body": json.dumps(result, default=json_serial)}


def is_gitlab_api_tester_failed():
    gitlab_token = os.environ["gitlabToken"]
    headers = {'PRIVATE-TOKEN': gitlab_token}
    response = requests.get("https://gitlab.sok.fi/api/v4/projects/1150/pipelines", headers=headers)
    
    gitlab_pipeline_json = response.json()
    statusval = gitlab_pipeline_json[0]['status']
    
    if statusval == "failed":
        return True
    else:
        return False


def has_alarms(d):

    if len(d) > 0:
        return True
    else:
        return False
        
def has_history_alarms(d):
    if len(d) > 0:
        return True
    else:
        return False
        
    
def is_pipe_running(d):
    r = False
    
    for item in d:
        if item['currentStatus'] == 'InProgress':
            r = True
            break
    return r
    
def get_running_pipe_list(d):
    pipelist = []

    for item in d:
        if item['currentStatus'] == 'InProgress':
            pipelist.append(item['name'])

    return pipelist

    
def is_pipe_failed(d):
    r = False
    
    for item in d:
        if item['currentStatus'] == 'Failed':
            r = True
            break
    return r
    
def get_failed_pipe_list(d):
    pipelist = []

    for item in d:
        if item['currentStatus'] == 'Failed':
            pipelist.append(item['name'])

    return pipelist


def get_metric(m):
    client = boto3.client('cloudwatch')
    return client.get_metric_statistics(**m)


def map_metric(m):
    try:
        return {'name': m['name'],
            'statistics': m['statistics'],
            'unit': m['unit'],
            'result': get_metric(m['request'])['Datapoints'][0][m['statistics']]}
    except Exception:
        return None

def get_metrics():
    return list(filter(None, (map(map_metric,metrics))))



def get_alarms():
    client = boto3.client('cloudwatch')
    alarms = client.describe_alarms()
    
    return list_alarms(alarms['MetricAlarms'])
    
    
def list_alarms(d):
    alarm_list = []
    
    for item in d:
        if item['StateValue'] != 'OK' and item['StateValue'] != 'INSUFFICIENT_DATA':
            alarm_list.append(item['AlarmName'])

    return alarm_list



def filter_not_alarm(d):
    if d['State'] == "ALARM":
        return True
    return False
    
def map_alarm_history(d):
    return {'AlarmName': d['AlarmName'],
            'Timestamp': d['Timestamp'],
            'State': json.loads(d['HistoryData'])["newState"]['stateValue']}

def get_alarms_history():
    client = boto3.client('cloudwatch')
    start=datetime.utcnow() - timedelta(hours=24)
    end=datetime.utcnow()
    response = client.describe_alarm_history(StartDate=start,EndDate=end,HistoryItemType='StateUpdate')
    return (list(filter (filter_not_alarm, (map(map_alarm_history, response['AlarmHistoryItems'])))))
    
    
def map_stages(d):
    if 'latestExecution' in d:
        return {"name": d['stageName'],
                "status": d['latestExecution']['status']}
    else:
        return {"name": d['stageName'],
                "status": "not-runned-yet"}


def get_pipeline_current_status(pipeline):
    client = boto3.client('codepipeline')
    res = client.get_pipeline_state(name=pipeline)
    execution_id =  res['stageStates'][0]['latestExecution']['pipelineExecutionId']
    status = client.get_pipeline_execution(pipelineName=pipeline,pipelineExecutionId=execution_id)
    pipeline_status = {"currentStatus": status['pipelineExecution']['status']}
    #stages = list(map(map_stages, res['stageStates']))
    return {**pipeline_status}


def map_statuses(d):
    return {'name': d['name'], **get_pipeline_current_status(d['name'])}


def get_pipelines():
    client = boto3.client('codepipeline')
    pipelines = client.list_pipelines()["pipelines"]

    return (list(map(map_statuses, pipelines)))
