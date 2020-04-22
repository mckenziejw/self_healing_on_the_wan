import json
from pprint import pprint
import os
from jinja2 import Environment, FileSystemLoader
import datetime
import time
import requests

class NorthstarConnector():

    def __init__(self, user, password, hostname, template_dir api_port = 8091, auth_port = 8443, api_version = "v2", tenant_id = 1, topology_id = 1):
        self.user = user
        self.password = password
        self.hostname = hostname
        self.api_port = api_port
        self.auth_port = auth_port
        self.api_version = api_version
        self.tenant_id = tenant_id
        self.topology_id = topology_id
        self.base_url = 'http://' + hostname + ':' + str(self.api_port) + '/Northstar/API/' + self.api_version + '/tenant/' + self.tenant_id + '/topology/' + self.topology_id + '/'
        self.node_url = self.base_url + 'nodes'
        self.link_url = self.base_url + 'links'
        self.lsp_url = self.base_url + 'te-lsps'
        self.token_headers = {'Content-Type': 'application/json'}
        self.token_url = 'https://' + hostname + ':' + self.auth_port + '/oauth2/token'
        self.token = get_token()
        self.api_header = {'Authorization': str('Bearer ' + self.token), 'Content-Type': 'application/json'}
        self.nodes = []
        self.links = []
        self.lsps = []
        self.template_dir = template_dir

    def get_token(self):
        data = requests.post(self.token_url, auth=(self.user, self.password), data='{"grant_type":"password","username":"' + self.user + '","password":"' + self.password + '"}', headers=token_headers, verify=False))
        if(data.json()['access_token']):
            return data.json()['access_token']
        else:
            return False

    def refresh_state(self):
        self.nodes = requests.get(self.node_url, headers=self.api_header, verify=False).json()
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
                return i
        return False
    
    def get_link_by_node_id_and_interface_name(self, node_id, int_name, refresh_state = True):
        if refresh_state:
            self.refresh_state()
        for link in self.links:
           if ((link['endA']['node']['id'] == node_id) and (link['endA']['interfaceName'] == int_name)) or ((link['endZ']['node']['id'] == node_id) and (link['endZ']['interfaceName'] == int_name)):
               return link
        return False

    def get_node_id_by_hostname(self, hostname):
        if refresh_state:
            self.refresh_state()
        for node in self.nodes:
            if node['hostName'] == hostname:
                return node['id']
        return False

    def create_maintenance(self, object_id, purpose, maintenance_type):
        current_time = datetime.datetime.utcnow().stroftime("%Y%m%d%H%M")
        if purpose == 'for_simulation':
            name = 'created_for_simulation'
            start = 3600
            end = 6000
        else:
            name = 'Healthbot-' + maintenance_type + '-health-alert-' + current_time
        