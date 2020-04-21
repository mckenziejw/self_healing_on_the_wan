import json
from pprint import pprint
import os
from jinja2 import Environment, FileSystemLoader
import datetime
import time
import requests

url = 'http://:8091/Northstar/API/v2/tenant/1/topology/1/'
node_url_test = url + 'nodes'

node_url = url + 'nodes'
link_url = url + 'links'
lsp_url = url + 'te-lsps'
token_url = 'https://:8443/oauth2/token'
maintenance_url = url + 'maintenances'
run_simulation_url = url + 'rpc/simulation'
hearders_token = {'Content-Type': 'application/json'}
user = '******'
password = '******'

def get_token():
    r = requests.post(token_url, auth=('******', '*******'), data='{"grant_type":"password","username":"******","password":"******"}', headers=hearders_token, verify=False)
    return r.json()['access_token']

token = get_token()
headers = {'Authorization': str('Bearer ' + token), 'Content-Type': 'application/json'}

def get_node_info(hostname):
    network_info = get_node()
    for i in network_info.json():
        if i['hostName'] == hostname:
            index_number = i['nodeIndex']
    return index_number

def get_link_info(linkname):
    network_info = get_link()
    for i in network_info.json():
        if i['name'] == linkname:
            index_number = i['linkIndex']
    return index_number

def get_link_info_from_ip(interface_ip):
    network_info = get_link()
    for i in network_info.json():
      if (i['endA']['ipv4Address']['address'] == interface_ip) or (i['endZ']['ipv4Address']['address'] == interface_ip):
        index_number = i['linkIndex']
    return index_number

def get_link_from_nodeID_and_interface(nodeID,interface_name):
    network_info = get_link()
    for i in network_info.json():
        if ((i['endA']['node']['id'] == nodeID) and (i['endA']['interfaceName'] == interface_name)) or ((i['endZ']['node']['id'] == nodeID) and (i['endZ']['interfaceName'] == interface_name)):
            link = i
    return link
   

def get_nodeID_from_hostname(hostname):
    network_info = get_node()
    for i in network_info.json():
        if i['hostName'] == hostname:
            nodeID = i['id']
    return nodeID

'''
def move_traffic():
    contents = open('new_path.json', 'rb').read()
    print(contents)
    r = requests.post(lsp_url, data=contents, headers=headers, verify=False)
    # print(r)
 
def move_traffic2():
    contents = open('new_path.json', 'rb').read()
    print(contents)
    r = requests.put(lsp_url, data=contents, headers=headers, verify=False)
    # print(r)

def move_traffic_back():
    contents = open('original_path.json', 'rb').read()
    print(contents)
    r = requests.post(lsp_url, data=contents, headers=headers, verify=False)
'''

def get_node():
    r = requests.get(node_url, headers=headers, verify=False)
    return (r)

def get_link():
    r = requests.get(link_url, headers=headers, verify=False)
    return (r)

def create_maintenance(payload):
    print(payload)
    r = requests.post(maintenance_url, data=payload, headers=headers, verify=False)
    return r

def delete_maintenance(maint_index):
    maint_index = str(maint_index)
    delete_maint_url = maintenance_url + '/' + maint_index
    r = requests.delete(delete_maint_url, headers=headers, verify=False)
    return r

def generate_maitenance_json(index_number, use, maintenance_type):
    #start = 1 for now
    # end = 6000 
    maintenance_type = maintenance_type
    current_time=datetime.datetime.utcnow().strftime("%Y%m%d%H%M")
    if use == 'for_simulation':
        name = 'created_for_simulation'
        start = 3600
        end = 6000
    else:
        name = 'Healthbot-' + maintenance_type + '-health-alert' + current_time
        start = 1
        end = 6000
    THIS_DIR = os.path.dirname(os.path.abspath('__file__'))
    j2_env = Environment(loader=FileSystemLoader(THIS_DIR),
                         trim_blocks=True)

    payload = j2_env.get_template('maintenance.j2').render(
        maintenance_type=maintenance_type,
        index_number=index_number,
        current_time=current_time,
        name=name,
        start_time=getTimeSeqUTC(start),
        end_time=getTimeSeqUTC(end)
    )
    return (payload)

'''
def generate_link_maitenance_json():
    index_number = get_link_info("L10.135.5.1_10.135.5.2")
    THIS_DIR = os.path.dirname(os.path.abspath(__file__))

    j2_env = Environment(loader=FileSystemLoader(THIS_DIR),
                         trim_blocks=True)

    payload = j2_env.get_template('maintenance.j2').render(
        maintenance_type='link',
        index_number=index_number,
        current_time=datetime.datetime.utcnow().strftime("%Y%m%d%H%M"),
        start_time=getTimeSeqUTC(1),
        end_time=getTimeSeqUTC(6000)
    )
    return payload
'''

def generate_link_traffic_threshold_payload(linkIndex,linkID,endA_ID,endZ_ID,endA_Threshold,endZ_Threshold):
    THIS_DIR = os.path.dirname(os.path.abspath('__file__'))
    j2_env = Environment(loader=FileSystemLoader(THIS_DIR),
                         trim_blocks=True)
    payload = j2_env.get_template('link_traffic_threshold.j2').render(
        linkID=linkID,
        linkIndex=linkIndex,
        endA_ID=endA_ID,
        endZ_ID=endZ_ID,
        endA_Threshold= endA_Threshold,
        endZ_Threshold= endZ_Threshold
    )
    return payload

def update_link_traffic_threshold(payload, linkIndex):
    print payload
    linkIndex = str(linkIndex)
    linkThresholdURL = link_url + '/' +  linkIndex 
    print linkThresholdURL
    r = requests.put(linkThresholdURL, data=payload, headers=headers, verify=False)
    return r

def getTimeSeqUTC(num):
    # tz = pytz.timezone('America/New_York')
    # a = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    a = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    b_start = time.mktime(time.strptime(a, '%Y-%m-%d %H:%M:%S')) + int(num) * 60
    dateA = str(time.strftime("%Y%m%d", time.localtime(b_start)))
    timeA = str(time.strftime("%H%M", time.localtime(b_start)))
    juniorTime = 'T'.join([dateA, timeA])
    endstr = "00"
    finalTime = ''.join([juniorTime, endstr])
    return finalTime + 'Z'


def set_overload_bit(router_to_configure):
    global user
    global password
    print "making confugration changes on " + router_to_configure
    print "#####################################"
    dev = Device(host=router_to_configure, user=user, password=password).open()
    with Config(dev) as cu:
        cu.load('set protocols isis overload', format='set')
        cu.pdiff()
        cu.commit()


def get_management_ip(host_name):
    network_info = './network_device.json'
    data = json.loads(open(network_info).read())
    for i in data['NetworkDeviceList']:
        # pprint(i)
        # i['NetworkDevice']['Name']
        if i['NetworkDevice']['Name'] == host_name:
            management_ip = i['NetworkDevice']['ManagementIp']
    return management_ip


def run_simulation(simulation_name):
    simulation_name = simulation_name
    simulation_type = "link"
    simulation_payload = '{"topoObjectType":"maintenance","topologyIndex":1,"elements":[{"type":"maintenance","maintenanceName":"' + simulation_name + '"},"' + simulation_type + '"]}'
    r = requests.post(run_simulation_url, data=simulation_payload, headers=headers, verify=False)
    return r


def get_simulation_report(simulationID):
    simulationID = simulationID
    simulation_report_url = url + 'rpc/simulation/' + simulationID + '/Report/L2_PeakSimRoute.r0' 
    r = requests.get(simulation_report_url, headers=headers, verify=False)
    return r


def check_if_simulation_pass():
    check_passed = 'true'
    simulation_name = 'created_for_simulation'
    simulation_type = "link"
    simulation_payload = '{"topoObjectType":"maintenance","topologyIndex":1,"elements":[{"type":"maintenance","maintenanceName":"' + simulation_name + '"},"' + simulation_type + '"]}'
    r = requests.post(run_simulation_url, data=simulation_payload, headers=headers, verify=False)
    simulationID=r.json()['simulationId'] 
    simulation_report_url = url + 'rpc/simulation/' + simulationID + '/Report/L2_PeakSimRoute.r0'
    report = requests.get(simulation_report_url, headers=headers, verify=False)
    if "NotRouted" in report.content:
      check_passed = 'false'
    return check_passed

def print_simulation_failure_content(report):
    lines = report.content.split('\n')
    for line in lines:
        if '#' in line:
            print line
        elif '*' in line:
            print line
        elif 'S' in line:
            line = line.split(',')
            print line[0] + ',' + line[1] + ',' + line[2] + ',' + line[3] + ',' + line[4] + ',' + line[5] + ','  + line[6]


  






   





