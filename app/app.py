# We need to import request to access the details of the POST request
from flask import Flask, request
from flask_restful import abort
import subprocess
import traceback
import json
from time import sleep
from pprint import pprint
import requests
import os
from NorthstarConnector import NorthstarConnector
requests.packages.urllib3.disable_warnings() 

headers_token = {'Content-Type': 'application/json'}
## Set default values for user, password and NS host
user = 'admin'
password = 'lab123'
ns_host = '172.25.11.100'
sms_receivers = None

# Check for environment variable settings (used with Docker)

if(os.environ.get('NS_USER') is not None):
    user = os.environ.get('NS_USER')
if(os.environ.get('NS_PASSWD') is not None):
    password = os.environ.get('NS_PASSWD')
if(os.environ.get('NS_HOST') is not None):
    ns_host = os.environ.get('NS_HOST')
if(os.environ.get('SMS_RECEIVER') is not None):
    sms_receivers = [os.environ.get('SMS_RECEIVER')]

template_dir = os.path.dirname(os.path.abspath('__file__'))
# Initialize NorthstarConnector

ns = NorthstarConnector(user=user, password=password, hostname=ns_host, template_dir=template_dir, sms_receivers=sms_receivers)

# Initialize the Flask application
app = Flask(__name__)

@app.route('/', methods=['POST'])
def app_message_post():
    print("START PROCESSING")
    if request.headers['Content-Type'] != 'application/json':
        print("not Json!") 
        abort(400, message="Expected Content-Type = application/json")
    try:
    # Extract global info
        data = request.json
        pprint(data)
        device_id = data['device-id']
        #hostname = data['hostname']
        group = data['group']
        rule = data['rule']
        severity = data['severity']
        trigger = data['trigger']
        #print("Source address is: " + data['keys']['source-address'])
        #int_index = ns.get_link_index_by_ip(data['keys']['source-address'])
        if rule == "probe_delay":
            print("received delay alert")
            int_index = ns.get_link_index_by_ip(data['keys']['source-address'])
            source_address = data['keys']['source-address']
            if trigger == 'probe_exceed' and severity == 'major':
                print(("HIGH DELAY DETECTED for  " + device_id + " " + source_address ))
                print("Begin exhaustive failure simulation")
                #create maintenance for simulation purpose
                new_maint = ns.create_maintenance(int_index, 'for_simulation', 'link') 
                if ns.check_if_simulation_pass():
                    print("Simulation passed")
                    print("HIGH DELAY DETECTED PUT LINK UNDER MAINTENANCE::")
                    ns.delete_maintenance(new_maint['maintenanceIndex'])
                    new_maint = ns.create_maintenance(int_index, 'for_maint', 'link')
#                    if(new_maint is not None):
#                        ns.sms_notify("A link has been put under maintenance due to high link delay. Link ID: int_index")
            elif severity == 'normal':
                print("DELAY back to normal. ")
                int_index = ns.get_link_index_by_ip(source_address)
                maint_id = ns.get_maintenance_id(object_type='link', object_id=int_index)
                if maint_id is not None:
                    resp = ns.complete_maintenance(maint_id)
                    resp_n = ns.delete_maintenance(maint_id)
        if rule == "check-system-cpu":
            if trigger == 're-cpu-utilization' and severity == 'major':
                #hostname = data['hostname']
                print("Recieved High CPU alert")
                print("Begin exhaustive failure simulation")
                print(data)
                hostname = data['device-id']
                print("host is: " + hostname)
                device_id = ns.get_node_id_by_hostname(hostname)
                #device_id = data['nodeIndex']
                new_maint = ns.create_maintenance(device_id, 'for_simulation', 'node')
                print("New Maintenance for sim")
                pprint(new_maint)
                if ns.check_if_simulation_pass():
                    sleep(10)
                    print("Simulation passed")
                    print("HIGH CPU PUT NODE UNDER MAINTENANCE::")
                    ns.delete_maintenance(new_maint['maintenanceIndex'])
                    new_maint = ns.create_maintenance(device_id, 'for_maint', 'node')
#                    if(new_maint is not None):
#                        ns.sms_notify("A node has been put under maintenance due to high CPU utilization. Node: device_id")
            elif severity == 'normal':
                print("CPU utilization back to normal. ")
                hostname = data['device-id']
                device_id = ns.get_node_id_by_hostname(hostname)
                maint_id = ns.get_maintenance_id(object_type='node', object_id=device_id)
                if maint_id is not None:
                    resp = ns.complete_maintenance(maint_id)
                    resp_n = ns.delete_maintenance(maint_id)
        print("###############################")
        return json.dumps({'result': 'OK'})

    #     # if playbook_name == "cpu_openconfig":
    #     #     print("received cpu high alert")
    #     #     if "exceeds high threshold" in message:
    #     #         print('CPU HIGH UTIL DETECTED for ' + device_id)
    #     #         print('PERFORMING EXHUASTIVE LINK FAILURE SIMULATION for ' + device_id)
    #     #         #create maintenance for simulation purpose
    #     #         rest_index_number = user_functions.get_node_info(device_id)
    #     #         rest_payload = user_functions.generate_maintenance_json(rest_index_number, 'for_simulation', 'node') 
    #     #         maintenance_event = user_functions.create_maintenance(rest_payload)
    #     #         maintenance_index = maintenance_event.json()['maintenanceIndex']
    #     #         check_simulation = user_functions.check_if_simulation_pass()
    #     #         print(("simulation result " + check_simulation))
    #     #         user_functions.delete_maintenance(maintenance_index)
    #     #         print("delete temp maintenace")
    #     #         if check_simulation == 'true':
    #     #             print('CPU HIGH UTIL DETECTED PUT NODE UNDER MAINTENANCE::')
    #     #             # pprint.pprint(data)
    #     #             #print "rest_node_name, rest_index_number" +  rest_node_name +  rest_index_number
    #     #             rest_payload = user_functions.generate_maintenance_json(rest_index_number, 'for_maint', 'node')
    #     #             print(rest_payload)
    #     #             user_functions.create_maintenance(rest_payload)
    #     #         else:
    #     #             print(('CANNOT PUT ' + device_id + ' UNDER MAINTENANCE. EXHUASTIVE FAILURE SIMULATION NOT PASSED'))
    #     #     elif "is normal" in message:
    #     #         #print 'DATA_INACTIVE :: ', pprint.pprint(data)
    #     #         print('CPU util back to normal. ')
    #     # print('###############################')
    #     # if playbook_name == "probe_delay":
    #     #     print("received delay alert")
    #     #     source_address = data['keys']['source-address']
    #     #     #print "interface-ip " + source_address
    #     #     #target_address = data['keys']['target_address']
    #     #     #print "message" + message
    #     #     if "exceeds delay threshold" in message:
    #     #         print(("HIGH DELAY DETECTED for  " + device_id + " " + source_address ))
    #     #         print(("PERFORMING EXHUASTIVE LINK FAILURE SIMULATION for " + device_id + " " + source_address))
    #     #         #create maintenance for simulation purpose
    #     #         rest_index_number = user_functions.get_link_info_from_ip(source_address)
    #     #         rest_payload = user_functions.generate_maintenance_json(rest_index_number, 'for_simulation', 'link')
    #     #         maintenance_event = user_functions.create_maintenance(rest_payload)
    #     #         maintenance_index = maintenance_event.json()['maintenanceIndex']
    #     #         check_simulation = user_functions.check_if_simulation_pass()
    #     #         print(("SIMULATION RESULT " + check_simulation))
    #     #         user_functions.delete_maintenance(maintenance_index)
    #     #         #print "delete temp maintenace"
    #     #         if check_simulation == "true":
    #     #             print("HIGH DELAY DETECTED PUT LINK UNDER MAINTENANCE::")
    #     #             # pprint.pprint(data)
    #     #             #print "rest_node_name, rest_index_number" +  rest_node_name +  rest_index_number
    #     #             rest_payload = user_functions.generate_maintenance_json(rest_index_number, 'for_maint', 'link')
    #     #             print(rest_payload)
    #     #             user_functions.create_maintenance(rest_payload)
    #     #         else:
    #     #             print("CANNOT PUT " + device_id + " " + source_address + " UNDER MAINTENANCE. EXHUASTIVE FAILURE SIMULATION NOT PASSED")
    #     #     elif "is normal" in message:
    #     #         #print 'DATA_INACTIVE :: ', pprint.pprint(data)
    #     #         print("DELAY back to normal. ")
    #     # print("###############################")
    #     # return json.dumps({'result': 'OK'})
    except Exception as e:
        pprint(e)
        abort(400, message="Exception processing request: {0}".format(e))
        traceback.print_exc()

if __name__ == '__main__':
    app.run(
        host="0.0.0.0",
        port=int("10000")
    )
