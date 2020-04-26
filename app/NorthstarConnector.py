import json
from pprint import pprint
import os
from jinja2 import Environment, FileSystemLoader
import datetime
import time
import requests
import pickle

class NorthstarConnector():

    def __init__(self, user, password, hostname, template_dir, api_port = 8443, auth_port = 8443, api_version = "v2", tenant_id = 1, topology_id = 1):
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
        self.maintenances = {}
        self.template_dir = template_dir
        self.maintenance_template = 'maintenance.j2'
        self.current_maintenance = None
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
        self.maintenances = requests.get(self.maintenance_url, headers=self.api_header, verify=False).json()
        self.links = requests.get(self.link_url, headers=self.api_header, verify=False).json()
        return True

    def get_node_index_by_hostname(self, hostname, refresh_state = True):
        if refresh_state:
            self.refresh_state()
        for node in self.nodes:
            if node['hostname'] == hostname:
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

    def get_node_id_by_hostname(self, hostname):
        if refresh_state:
            self.refresh_state()
        for node in self.nodes:
            if node['hostName'] == hostname:
                return node['id']
        return False
    
    def get_maintenance_id(self, object_type, object_id):
        # Note: this assumes no more than one maintenance active per object
        for m in self.maintenances:
            for e in m['elements']:
                if e['index'] == object_id and e['topoObjectType'] == object_type:
                    return m['maintenanceIndex']
        return None      

    def create_maintenance(self, object_id, purpose, maintenance_type):
        current_time = datetime.datetime.utcnow().strftime("%Y%m%d%H%M")
        if self.get_maintenance_id(object_type=maintenance_type, object_id=object_id) is None:
            start = 1
            end = 6000 
            name = 'Healthbot-' + maintenance_type + '-health-alert-' + current_time
            jinja_env = Environment(loader=FileSystemLoader(self.template_dir), trim_blocks=True)
                payload = jinja_env.get_template(self.maintenance_template).render(
                maintenance_type=maintenance_type,
                index_number = object_id,
                current_time=current_time,
                name=name,
                start_time=self.getTimeSeqUTC(start),
                end_time=self.getTimeSeqUTC(end)
            )
            data = requests.post(self.maintenance_url, data=payload, headers=self.api_header,verify=False)
            if data.json()['maintenanceIndex']:
                self.maintenances[data.json()['maintenanceIndex']] = data.json()
                return data.json()
            else:
                return None
        else:
            print("Maintenance already exists for {} with ID {}".format(maintenance_type, object_id))
            return None
    
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
        update_url = self.maintenance_url + '/' + str(maintenance_id))
        self.maintenances[maintenance_id]['status'] = 'completed'
        payload = json.dumps(self.maintenances[maintenance_id])
        data = requests.put(update_url, data=payload, headers=self.api_header, verify=False)
        return data

    def delete_maintenance(self, maintenance_id):
        del_url = self.maintenance_url + '/' + str(maintenance_id)
        data = requests.delete(del_url, headers=self.api_header, verify=False)
        if data:
            self.maintenances.pop(maintenance_id)
            return data
        else:
            return None

    
