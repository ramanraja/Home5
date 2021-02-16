from flask import current_app as app  
from flask import Flask, render_template, request
from random import randint
from datetime import datetime
import json

#from intof.Router import onboard_device
#import intof.Router.onboard_device as onboard_device
#from intof.Models import Device, Relsen 

from intof import db
from intof.Models import User
from intof.Decorator import token_required
from intof.Authenticator import insert_user

import intof.Router as r
import intof.Models as m
import intof.Bridge as b

current_user = 'Anonymous'  # place holder till authentication is implemented
#----------------------------------------------------------------------------------------
# Helper methods
#----------------------------------------------------------------------------------------
def housekeeper_test_method():
    print ('\n--- I am the housekeeper stub ! ---\n')
    
DPRINT_ENABLED = True
def dprint (*args):
    #app.logger.info (*args)
    if DPRINT_ENABLED:
        print (*args)
        
#----------------------------------------------------------------------------------------
# Housekeeping routes
#----------------------------------------------------------------------------------------
         
@app.route('/') 
@app.route ('/index')         
@app.route ('/menu')
def menu ():
    return (render_template('menu.html'))
    
# unit tests and API documentation
@app.route('/test', methods =['GET']) 
def test (): 
    #b.bridge_test_method()
    return (render_template('tester.html'))
    
@app.route('/random', methods =['GET']) 
def random (): 
    return ({'random' : randint(0, 10000)})

@app.route('/secure/random', methods =['GET']) 
@token_required
def secure_random (current_user): 
    return ({'secure_random' : randint(0, 10000)})
                
@app.route ('/secure')
@token_required
def secure_page (current_user):
    msg = 'Authenticated user: {}'.format(current_user)
    print (msg)
    return ({'result' : 'authenticated.', 'current_user' : str(current_user)}, 200)
    
@app.route ('/insecure')
def insecure_page ():
    return ({'result' : 'this is an open page'}, 200)
        
# buttons to control a real device            
@app.route('/buttons')
def rooot():
    return render_template ('buttons.html')     
                    
# socket to MQTT bridge; you can send an arbitrary MQTT payload to any topic      
# *** CAUTION: This is a remote trap door from the Internet to your local MQTT server! ***
# Disable it in production mode
@app.route('/bridge')
def bridge():
    return render_template ('bridge.html')  
    # return ('MQTT bridge has been disabled')
                
@app.route('/get/time', methods=['GET'])
def get_time():
    time = datetime.now().strftime ("%Y-%d-%m %H:%M:%S")
    retval = {'hub_time' : time}
    dprint (retval)
    return (retval)
    
@app.route('/echo', methods=['GET','POST'])
def echo_input():
    dprint ('\nRequest: ', request)
    if request.json is None:
        retval = {'input' : 'NULL'}
    else:
        retval = request.json
    print (retval)
    return (retval)
    
@app.route('/deliberately/crash/app', methods=['GET'])    
def crash_app():
    dprint ('\nRequest: ', request)
    print ('Crashing the system! Just for testing..')
    raise Exception ('This session was deliberatedly test-crashed.')
    return ({'error' : 'test crash'})    
    
@app.route('/add/test/users') 
def add_test_users():
    insert_user ('ra@ja.com', 'raja', 'raja')
    insert_user ('ad@min.com', 'admin', 'admin')    
    return ({'result': 'Test users added'})            
    
    
@app.route ('/remove/user')
def remove_user ():
    print ('{} is removing user...'.format(current_user))    
    mail = request.args.get('email')
    if (not mail):
        return ({'error' : 'email id is required'})
    usr = User.query.filter_by (email=mail).first()
    if (not usr):
        return ({'error' : 'invalid email'})
    db.session.delete(usr)
    db.session.commit()
    return ({'result': 'One user record removed'})

        
@app.route ('/remove/all/users')
def remove_all_users ():
    print ('{} is removing all user records...'.format(current_user))    
    usrs = User.query.all()
    print ('{} records found.'.format(len(usrs)))
    for u in usrs:
        db.session.delete(u)
    db.session.commit()
    return ({'result': 'All user records removed'})
 
            
@app.route('/list/users', methods =['GET']) 
def get_all_users (): 
    users = User.query.all() 
    output = [] 
    for user in users: 
        output.append({ 
            'name' : user.name, 
            'email' : user.email, 
            'password_hash' : user.password[:25]+'***'+user.password[-4:]
        }) 
    return ({'users': output})   
    
def save_network_config(netconfig):    # TODO: implement this!
    print ('THIS IS A NETWORK CONFIG STUB:')
    print (netconfig)
    return True
    # TODO: how to restart the hub after this call?
#-------------------------------------------------------------------------------------- 
# Add Test data
#-------------------------------------------------------------------------------------- 

@app.route('/add/minimal/data') 
def add_minimal_data():
    dprint(add_test_users())
    
    DEV1 = 'fan'
    DEV2 = 'portico'
    DEV3 = 'hydro'
    DEV4 = 'labs1'
    DEV5 = 'coffee'  # this is not enabled initially
    # TODO: all the following calls return False if they fail. Handle it!
    r.insert_device (device_id=DEV1, num_relays=1, enabled=True)
    r.insert_device (device_id=DEV2, num_relays=2, enabled=True)
    r.insert_device (device_id=DEV3, num_relays=2, enabled=True)
    r.insert_device (device_id=DEV4, num_relays=4, enabled=True)
    r.insert_device (device_id=DEV5, num_relays=2, enabled=False)  # onboard it in disabled status
    
    r.insert_relsen (device_id=DEV1, relsen_id='POWER')
    r.insert_relsen (device_id=DEV2, relsen_id='POWER1')
    r.insert_relsen (device_id=DEV2, relsen_id='POWER2')
    r.insert_relsen (device_id=DEV3, relsen_id='POWER1')
    r.insert_relsen (device_id=DEV3, relsen_id='POWER2')
    r.insert_relsen (device_id=DEV4, relsen_id='POWER1')
    r.insert_relsen (device_id=DEV4, relsen_id='POWER2')
    r.insert_relsen (device_id=DEV4, relsen_id='POWER3')
    r.insert_relsen (device_id=DEV4, relsen_id='POWER4')
    r.insert_relsen (device_id=DEV5, relsen_id='POWER1')
    r.insert_relsen (device_id=DEV5, relsen_id='POWER2')    
    return ({'result': '5 Test devices added (if not existing)'})   
    

@app.route('/add/test/data') 
def add_test_data():    
    dprint(add_test_users())
    
    DEV1 = 'AA12345'
    DEV2 = 'BB45678'
    DEV3 = 'CC67890'  
    DEV4 = 'labs1'
    
    # TODO: all the following calls return False if they fail. Handle it!
    # device
    r.insert_device (device_id=DEV1, fallback_id='fb_DVES0BC870', mac='A2390BC870', ip='192.168.0.2',
                hardware_type="Generic", num_relays=1, num_sensors=1, enabled=True)
    r.insert_device (device_id=DEV2, fallback_id='fb_DVESBC8991', mac='B9034BC8991', ip='192.168.0.3',
                hardware_type="RND.MCU.AL2", num_relays=2, num_sensors=1, enabled=True)
    r.insert_device (device_id=DEV3, fallback_id='fb_DVES9021A8', mac='C0B5E59021A8', ip='192.168.0.4',
                hardware_type="Generic", num_relays=4, num_sensors=0, enabled=True)
    r.insert_device (device_id=DEV4, fallback_id='fb_DVES0C45A1', mac='FF34E0C45A1', ip='192.168.0.5',
                hardware_type="MCU.4.PIR.RAD.2R", num_relays=4, num_sensors=1, enabled=True)                
                
    # relsen
    sched1 = json.dumps({"schedule":[["6:30","7:25"],["18:0","19:05"]]})
    sched2 = json.dumps({"schedule":[["11:0","12:10"],["13:0","14:50"]]})
    sched3 = json.dumps({"schedule":[["10:0","15:15"]]})
    sched4 = json.dumps({"schedule":[["9:0","12:0"],["12:10","12:40"],["16:0","18:30"]]}) # the third one will be ignored; only 2 schedules per relay

    r.insert_relsen (device_id=DEV1, relsen_id='POWER1', relsen_name='Guest fan', relsen_type='Fan', 
                room_name='Master bed room', room_type='Bed room', group_name='Ground floor',
                schedule=None, repeat=False)    
    r.insert_relsen (device_id=DEV1, relsen_id='SENSOR', relsen_name='Temperature', relsen_type='Temperature sensor', 
                room_name='Guest room', room_type='Bed room', group_name='Sensors',
                schedule=sched1, repeat=False)    
    r.insert_relsen (device_id=DEV1, relsen_id='SENSOR', relsen_name='Humidity', relsen_type='Humidity sensor', 
                room_name='Master bed room', room_type='Bed room', group_name='Sensors',
                schedule=None, repeat=False)   
    r.insert_relsen (device_id=DEV2, relsen_id='POWER1', relsen_name='Bed room fan', relsen_type='Fan', 
                room_name='Master bed room', room_type='Bed room', group_name='Ground floor',
                schedule=sched2, repeat=True)    
    r.insert_relsen (device_id=DEV2, relsen_id='POWER2', relsen_name='Bed room light', relsen_type='Tube light', 
                room_name='Master bed room', room_type='Bed room', group_name='Ground floor',
                schedule=sched3, repeat=True)    
    r.insert_relsen (device_id=DEV2, relsen_id='SENSOR', relsen_name='Garage door', relsen_type='Door sensor', 
                room_name='Garage', room_type='Garage', group_name='Sensors',
                schedule=None, repeat=False)                    
    r.insert_relsen (device_id=DEV3, relsen_id='POWER1', relsen_name='Bath light', relsen_type='Bulb', 
                room_name='Main bath room', room_type='Bath room', group_name='Ground floor',
                schedule=sched1, repeat=True)    
    r.insert_relsen (device_id=DEV3, relsen_id='POWER2', relsen_name='Corridor light', relsen_type='Bulb', 
                room_name='Varanda', room_type='Corridor', group_name='Ground floor',
                schedule=None, repeat=False)    
    r.insert_relsen (device_id=DEV3, relsen_id='POWER3', relsen_name='Sit out light', relsen_type='Flood light', 
                room_name='sit out', room_type='Balcony', group_name='First floor',
                schedule=None, repeat=False)     
    r.insert_relsen (device_id=DEV3, relsen_id='POWER4', relsen_name='Balcony light', relsen_type='Tube light', 
                room_name='sit out', room_type='Balcony', group_name='First floor',
                schedule=sched3, repeat=False)     
    r.insert_relsen (device_id=DEV4, relsen_id='POWER1', relsen_name='AC', relsen_type='Air conditioner', 
                room_name='Kids bed room', room_type='Bed room', group_name='First floor',
                schedule=sched1, repeat=True)   
    r.insert_relsen (device_id=DEV4, relsen_id='POWER2', relsen_name='Geyser', relsen_type='Water heater', 
                room_name='Kids bath room', room_type='Bath room', group_name='First floor',
                schedule=sched4, repeat=True)   
    r.insert_relsen (device_id=DEV4, relsen_id='POWER3', relsen_name='AC', relsen_type='Air conditioner', 
                room_name='Grandma\'s bed room', room_type='Bed room', group_name='Ground floor',
                schedule=sched4, repeat=True)   
    r.insert_relsen (device_id=DEV4, relsen_id='POWER4', relsen_name='Fan', relsen_type='Fan', 
                room_name='Grandma\'s bath room', room_type='Bath room', group_name='Ground floor',
                schedule=sched4, repeat=True)                 
    r.insert_relsen (device_id=DEV4, relsen_id='SENSOR', relsen_name='Garage door', relsen_type='Door sensor', 
                room_name='Garage', room_type='Basement', group_name='Sensors',
                schedule=None, repeat=False)       
    # status
    stat1 = json.dumps({"Relays":[1,0,1,0]})
    stat2 = json.dumps({"Relays":[1,0,1,0]})
    stat3 = json.dumps({"Relays":[1,0,1,0]})
    stat4 = json.dumps({"Relays":[1,0,1,0]})
    sensor1 = json.dumps({"Temperature":31.6, "Humidity":76.1})
    sensor2 = json.dumps({"Temperature":22.2, "Humidity":66.9})
    sensor3 = json.dumps({"Light":786})
    sensor4 = json.dumps({"Light":1022})
    sensor5 = json.dumps({"Garage door":"Open"})
    
    r.insert_status (device_id=DEV1, relay_status=stat1, event_type='Response', online=True)
    r.insert_status (device_id=DEV1, sensor_values=sensor1, event_type='Autonomous', online=True)
    r.insert_status (device_id=DEV2, relay_status=stat2, event_type='Event', online=True)
    r.insert_status (device_id=DEV3, relay_status=stat3, sensor_values=sensor2, event_type='Health', online=True)
    r.insert_status (device_id=DEV4, relay_status=stat4, sensor_values=sensor3, event_type='Health', online=True)
    r.insert_status (device_id=DEV4, sensor_values=sensor5, event_type='Event', online=True)
    return ({'result': '4 Test devices added (if not existing)'})   
    
# Simulate device discovery   
@app.route('/simul/discover/devices') 
def simul_discover_devices():    
    jnew_devices = {'intof_B0871F': ['POWER1', 'POWER2', 'POWER3', 'POWER4'],
                     'intof_C8802C' : ['POWER1', 'POWER2', 'SENSOR']}
    return (jnew_devices)
        
# Simulate an onboarding operation    
@app.route('/simul/onboard/device') 
def simul_onboard_device():    
    jnew_device = {'device_id' : 'intof_A9417E', 'relsen_list' : ['POWER1', 'POWER2', 'SENSOR']}
    if r.onboard_device (jnew_device):
        return {'result' : 'device onboarded successfully'}
    return {'error' : 'failed to onboard device'}

# Simulate bulk onboarding operation    
@app.route('/simul/bulk/onboard') 
def simul_bulk_onboard():    
    jnew_devices = {'intof_B0487C': ['POWER1', 'POWER2', 'POWER3', 'POWER4'], 'intof_C1432D': ['POWER1'], 'intof_F09A82': ['POWER1', 'POWER2', 'SENSOR']}
    if r.bulk_onboard_devices (jnew_devices):
        return {'result' : 'all devices onboarded successfully'}
    return {'error' : 'failed to onboard at least one device'}
    
    
@app.route('/add/devices', methods =['GET', 'POST'])   # TODO: this is a place holder for the actual add_devices
def simul_add_devices():     #                         # TODO: implement the actual function in Router 
    simul_bulk_onboard()
    return {'result' : 'Your new devices will be onboarded now. This may take several minutes'}


# Simulate an update_device operation    
@app.route('/simul/update/device') 
def simul_update_device():
    dev = m.Device.query.filter_by (device_id='labs1').first()
    if (not dev):
        return {'error' : 'labs1 : invalid device_id'}
    en = not(dev.enabled)  # toggle the current status
    jupdate = {'device_id' : 'labs1', 'enabled' : en}
    r.update_device (jupdate)
    return {'result' : 'device labs1 updated'}
    
# Simulate an update_relsen operation        
@app.route('/simul/update/relsen') 
def simul_update_relsen():
    rs = m.Relsen.query.filter_by (device_id='labs1', relsen_id='POWER1').first()
    if (not rs):
        return {'error' : 'invalid device_id or relsen_id'}
    jupdate = {
        'device_id':'labs1', 'relsen_id':'POWER2',
        'relsen_name':'Table fan', 'relsen_type': 'Fan',
        'room_name':'Grandpa\'s room', 'room_type': 'Dining room', 'group_name':'Basement',
        'schedule': [["10:00","11:30"],["17:20","18:45"]], 
        'repeat':False
    }
    r.update_relsen (jupdate)
    return {'result' : 'relsen {}/{} updated'.format(jupdate['device_id'], jupdate['relsen_id'])}    
        
# simulate adding timer schedules        
@app.route('/simul/update/schedule') 
def simul_update_schedule():
    device_id = 'labs1'
    relsen_id = 'POWER2'
    timer_list = [["6:20", "7:05"], ["12:30", "14:45"], ["17:0","19:10"]] 
    repeat = False
    if b.update_timer (device_id, relsen_id, timer_list, repeat):
        return {'result' : 'schedule for labs1 updated'}    
    else:
        return {'error' : 'device schedule could not be updated'}    

# store WIFI credentials and MQTT broker IP address on the hub
# SECURITY NOTE: for emergency use, we allow configuration using plain text URL parameters. This is to be disabled eventually ! ***
@app.route('/configure/network', methods =['GET', 'POST']) 
def configure_network():
    netconfig = None
    if (request.method=='GET'):
        wifi_ssid = request.args.get('wifi_ssid')
        if (not wifi_ssid):
            return ({'error' : 'WIFI AP name is required'})
        wifi_password = request.args.get('wifi_password')
        if (not wifi_password):  # NOTE: it can be a zero length string, allowed
            return ({'error' : 'WIFI password is required'})
        hub_ip = request.args.get('hub_ip')
        if (not hub_ip):
            return ({'error' : 'Hub IP address is required'})
        netconfig = {'wifi_ssid' : wifi_ssid,  'wifi_password' : wifi_password, 'hub_ip' : hub_ip}
            
    else:   # it was a POST
        if (not request.json):
            return ({'error':'invalid network configuration'})
        netconfig = {
            'wifi_ssid' : request.json.get('wifi_ssid'),  
            'wifi_password' : request.json.get('wifi_password'), 
            'hub_ip' : request.json.get('hub_ip')
        }
    if (save_network_config (netconfig)):
        return {'result' : 'Network credentials updated. Your Hub will restart now!'}    
    else:
        return {'error' : 'Network credentials could not be updated'}  
         
#from intof.Decorator import token_required
