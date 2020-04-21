# We need to import request to access the details of the POST request
from flask import Flask, request
from flask_restful import abort
import subprocess
import json
import pprint
import requests
import os
import user_functions
requests.packages.urllib3.disable_warnings() 

# Initialize the Flask application
app = Flask(__name__)

@app.route('/', methods=['POST'])
def app_message_post():
    print("#################  Start  #######################")
    if request.headers['Content-Type'] != 'application/json':
        abort(400, message="Expected Content-Type = application/json")
    try:
        data = request.json
        print(data)
        message = data['message']
        print(("message " + message))
        playbook_name = data['keys']['_playbook_name']
        print(("playbook_name " + playbook_name))
        #test_name = data['keys']['test-name']
        #print "interface-name " + test_name 
        device_id = data['device-id']
        #print device_id + "  " + message
        #if spec['eventRuleId'] == g_rule_id:
        #    state = status['state']
        #    device_id = status['entityId']
        #    if state == "active" and device_id == g_device_id:
        #        print 'DATA_ACTIVE :: ', pprint.pprint(data)
        #        user_functions.move_traffic()
        #        print 'traffic detoured and Slack was notified'
        #    elif state == "inactive":
        #        #print 'DATA_INACTIVE :: ', pprint.pprint(data)
        #        print 'LSP path can be changed back'
        #return json.dumps({'result': 'OK'})
        if playbook_name == "cpu_openconfig":
            print("received cpu high alert")
            if "exceeds high threshold" in message:
                print('CPU HIGH UTIL DETECTED for ' + device_id)
                print('PERFORMING EXHUASTIVE LINK FAILURE SIMULATION for ' + device_id)
                #create maintenance for simulation purpose
                rest_index_number = user_functions.get_node_info(device_id)
                rest_payload = user_functions.generate_maitenance_json(rest_index_number, 'for_simulation', 'node') 
                maintenance_event = user_functions.create_maintenance(rest_payload)
                maintenance_index = maintenance_event.json()['maintenanceIndex']
                check_simulation = user_functions.check_if_simulation_pass()
                print(("simulation result " + check_simulation))
                user_functions.delete_maintenance(maintenance_index)
                print("delete temp maintenace")
                if check_simulation == 'true':
                    print('CPU HIGH UTIL DETECTED PUT NODE UNDER MAINTENANCE::')
                    # pprint.pprint(data)
                    #print "rest_node_name, rest_index_number" +  rest_node_name +  rest_index_number
                    rest_payload = user_functions.generate_maitenance_json(rest_index_number, 'for_maint', 'node')
                    print(rest_payload)
                    user_functions.create_maintenance(rest_payload)
                else:
                    print(('CANNOT PUT ' + device_id + ' UNDER MAINTENANCE. EXHUASTIVE FAILURE SIMULATION NOT PASSED'))
            elif "is normal" in message:
                #print 'DATA_INACTIVE :: ', pprint.pprint(data)
                print('CPU util back to normal. ')
        print('###############################')
        if playbook_name == "probe_delay":
            print("received delay alert")
            source_address = data['keys']['source-address']
            #print "interface-ip " + source_address
            #target_address = data['keys']['target_address']
            #print "message" + message
            if "exceeds delay threshold" in message:
                print(("HIGH DELAY DETECTED for  " + device_id + " " + source_address ))
                print(("PERFORMING EXHUASTIVE LINK FAILURE SIMULATION for " + device_id + " " + source_address))
                #create maintenance for simulation purpose
                rest_index_number = user_functions.get_link_info_from_ip(source_address)
                rest_payload = user_functions.generate_maitenance_json(rest_index_number, 'for_simulation', 'link')
                maintenance_event = user_functions.create_maintenance(rest_payload)
                maintenance_index = maintenance_event.json()['maintenanceIndex']
                check_simulation = user_functions.check_if_simulation_pass()
                print(("SIMULATION RESULT " + check_simulation))
                user_functions.delete_maintenance(maintenance_index)
                #print "delete temp maintenace"
                if check_simulation == "true":
                    print("HIGH DELAY DETECTED PUT LINK UNDER MAINTENANCE::")
                    # pprint.pprint(data)
                    #print "rest_node_name, rest_index_number" +  rest_node_name +  rest_index_number
                    rest_payload = user_functions.generate_maitenance_json(rest_index_number, 'for_maint', 'link')
                    print(rest_payload)
                    user_functions.create_maintenance(rest_payload)
                else:
                    print("CANNOT PUT " + device_id + " " + source_address + " UNDER MAINTENANCE. EXHUASTIVE FAILURE SIMULATION NOT PASSED")
            elif "is normal" in message:
                #print 'DATA_INACTIVE :: ', pprint.pprint(data)
                print("DELAY back to normal. ")
        print("###############################")
        """
        if event_rule_id == AppFormixInterfaceL3IncompleteEventID:
            print "Received interface l3 incomplete alert"
            if state == "active":
                rest_payload = user_functions.generate_link_maitenance_json()
                print rest_payload
                user_functions.create_maintenance(rest_payload)
                print 'Put problematic link into maintenance mode'
            elif state == "inactive":
            # print 'DATA_INACTIVE :: ', pprint.pprint(data)
                print 'link back to normal. you can complete the maintenance event'
        """
        return json.dumps({'result': 'OK'})
    except Exception as e:
        abort(400, message="Exception processing request: {0}".format(e))
        print('...')


if __name__ == '__main__':
    app.run(
        host="0.0.0.0",
        port=int("10000")
    )
