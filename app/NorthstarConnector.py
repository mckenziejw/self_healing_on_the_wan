import json
from pprint import pprint
import os
from jinja2 import Environment, FileSystemLoader
import datetime
import time
import requests
import pickle
from twilio import twiml
# twilio number (218) 396-2134
class NorthstarConnector():

    def __init__(self, user, password, hostname, template_dir, api_port = 8443, auth_port = 8443, api_version = "v2", tenant_id = 1, topology_id = 1, sms_receivers = None, account_sid = 'AC1707c740349f4ef59ad13c281622e543', auth_token = 'f28460c4b4180cc10182e682ce5c69e0'):
        self.user = user
        self.password = password
        self.hostname = hostname
        self.api_port = api_port
        self.auth_port = auth_port
        self.api_version = api_version
        self.tenant_id = tenant_id
        self.topology_id = topology_id
        self.base_url = 'https://' + hostname + ':' + str(self.api_port) + '/Northstar/API/' + self.api_version + '/tenant/' + str(self.tenant_id) + '/topology/' + str(self.topology_id) + '/'
        self.node_url = self.base_url + 'nodes'
        self.link_url = self.base_url + 'links'
        self.lsp_url = self.base_url + 'te-lsps'
        self.maintenance_url = self.base_url + 'maintenances'
        self.simulation_url = self.base_url + 'rpc/simulation'
        self.token_headers = {'Content-Type': 'application/json'}
        self.token_url = 'https://' + hostname + ':' + str(self.auth_port) + '/oauth2/token'
        self.token = self.get_token()
        self.api_header = {'Authorization': str('Bearer ' + self.token), 'Content-Type': 'application/json'}
        self.nodes = []
        self.links = []
        self.lsps = []
        self.maintenances = dict()
        self.template_dir = template_dir
        self.maintenance_template = 'maintenance.j2'
        self.current_maintenance = None
        self.sms_receivers = sms_receivers
        self.auth_token = auth_token
        self.account_sid = account_sid
        print("initialized")
    

    def get_token(self):
        data = requests.post(self.token_url, auth=('admin', 'password'), data='{"grant_type":"password","username":"admin","password":"lab123"}', headers=self.token_headers, verify=False)
        payload = {
        "grant_type": "password",
        "username": "admin",
        "password": "lab123"
        }
        #pprint(payload)
        #pprint(self.token_url)
        #data = requests.post(self.token_url, auth=(self.user, self.password), data=payload, headers=self.token_headers, verify=False)
        #pprint(data.json())
        if(data.json()['access_token']):
            return data.json()['access_token']
        else:
            return False

    def refresh_state(self):
        print("refreshing state")
        self.nodes = requests.get(self.node_url, headers=self.api_header, verify=False).json()
        #pprint(self.nodes)
        self.maintenances = self.parse_maintenances()
        #pprint(self.maintenances)
        self.links = requests.get(self.link_url, headers=self.api_header, verify=False).json()
        return True

    def parse_maintenances(self):
        maint_list = requests.get(self.maintenance_url, headers=self.api_header, verify=False).json()
        out_dict = {}
        for m in maint_list:
            out_dict[m['maintenanceIndex']] = m
        return out_dict

    def get_node_index_by_device(self, device, refresh_state = True):
        if refresh_state:
            self.refresh_state()
        for node in self.nodes:
            if node['nodeIndex'] == device:
                i = node['nodeIndex']
                return i
        return False

    def get_link_index_by_ip(self, ip, refresh_state = True):
        if refresh_state:
            self.refresh_state()
        for link in self.links:
            if (link['endA']['ipv4Address']['address'] == ip) or (link['endZ']['ipv4Address']['address'] == ip):
                i = link['linkIndex']
                print("Found link! link index: " + str(i))
                return i
        return False
    
    def get_link_by_node_id_and_interface_name(self, node_id, int_name, refresh_state = True):
        if refresh_state:
            self.refresh_state()
        for link in self.links:
           if ((link['endA']['node']['id'] == node_id) and (link['endA']['interfaceName'] == int_name)) or ((link['endZ']['node']['id'] == node_id) and (link['endZ']['interfaceName'] == int_name)):
               print(link)
               return link
        return False

    def get_node_id_by_hostname(self, hostname, refresh_state = True):
        if refresh_state:
            self.refresh_state()
        for node in self.nodes:
            if node['hostName'] == hostname:
                return node['nodeIndex']
        return False
    
    def get_maintenance_id(self, object_type, object_id):
        # Note: this assumes no more than one maintenance active per object
        for k, m in self.maintenances.items():
            print("Checking maintenance: ")
            pprint(m)
            for e in m['elements']:
                if e['index'] == object_id and e['topoObjectType'] == object_type:
                    return m['maintenanceIndex']
        return None      

    def create_maintenance(self, object_id, purpose, maintenance_type):
        current_time = datetime.datetime.utcnow().strftime("%Y%m%d%H%M")
        if purpose == 'for_simulation':
            start = 3600
            end = 6000
            name = 'created_for_simulation'
        else:
            start = 1
            end = 6000 
            name = 'Healthbot-' + maintenance_type + '-health-alert-' + current_time
        if self.get_maintenance_id(object_type=maintenance_type, object_id=object_id) is None:
            jinja_env = Environment(loader=FileSystemLoader(self.template_dir), trim_blocks=True)
            payload = jinja_env.get_template(self.maintenance_template).render(
            maintenance_type=maintenance_type,
            index_number = object_id,
            current_time=current_time,
            name=name,
            start_time=self.getTimeSeqUTC(start),
            end_time=self.getTimeSeqUTC(end)
            )
            pprint(payload)
            data = requests.post(self.maintenance_url, data=payload, headers=self.api_header,verify=False)
            print("received something")
            pprint(data.json())
            if data.json()['maintenanceIndex']:
                print("updating maintenances")
                i = data.json()['maintenanceIndex']
                print(self.maintenances)
                self.maintenances[i] = data.json()
                return data.json()
            else:
                return None
        else:
            print("Maintenance already exists for {} with ID {}".format(maintenance_type, object_id))
            return None

    def sms_notify(self, message):
        client = Client(self.account_sid, self.auth_token)
        for receiver in self.sms_receivers:
            msg = client.messages.create(body=message,from_='+15032073257',to=receiver)
        return True
    
    def getTimeSeqUTC(self, num):
        a = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        b_start = time.mktime(time.strptime(a, '%Y-%m-%d %H:%M:%S')) + int(num) * 60
        dateA = str(time.strftime("%Y%m%d", time.localtime(b_start)))
        timeA = str(time.strftime("%H%M", time.localtime(b_start)))
        juniorTime = 'T'.join([dateA, timeA])
        endstr = "00"
        finalTime = ''.join([juniorTime, endstr])
        return finalTime + 'Z'

    def complete_maintenance(self, maintenance_id):
        print("settings status to complete")
        update_url = self.maintenance_url + '/' + str(maintenance_id)
        self.maintenances[maintenance_id]['status'] = 'completed'
        payload = json.dumps(self.maintenances[maintenance_id])
        data = requests.put(update_url, data=payload, headers=self.api_header, verify=False)
        return data

    def delete_maintenance(self, maintenance_id):
        print("deleting maintenance")
        del_url = self.maintenance_url + '/' + str(maintenance_id)
        data = requests.delete(del_url, headers=self.api_header, verify=False)
        if data:
            self.maintenances.pop(maintenance_id)
            return data
        else:
            return None

    def run_simulation(self, simulation_name):
        simulation_name = simulation_name
        simulation_type = "link"
        simulation_payload = '{"topoObjectType":"maintenance","topologyIndex":1,"elements":[{"type":"maintenance","maintenanceName":"' + simulation_name + '"},"' + simulation_type + '"]}'
        r = requests.post(run_simulation_url, data=simulation_payload, headers=headers, verify=False)
        return r
    
    def check_if_simulation_pass(self):
        check_passed = 'true'
        simulation_name = 'created_for_simulation'
        simulation_type = "link"
        simulation_payload = '{"topoObjectType":"maintenance","topologyIndex":1,"elements":[{"type":"maintenance","maintenanceName":"' + simulation_name + '"},"' + simulation_type + '"]}'
        r = requests.post(self.simulation_url, data=simulation_payload, headers=self.api_header, verify=False)
        simulationID=r.json()['simulationId'] 
        simulation_report_url = self.base_url + 'rpc/simulation/' + simulationID + '/Report/L2_PeakSimRoute.r0'
        report = requests.get(simulation_report_url, headers=self.api_header, verify=False)
        if "NotRouted" in report.content:
            check_passed = 'false'
        return check_passed

    
