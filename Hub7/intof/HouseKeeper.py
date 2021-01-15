from flask import current_app as app  
from flask import Flask, render_template, request
from random import randint
from datetime import datetime
import json
#from intof.Router import onboard_device
#import intof.Router.onboard_device as onboard_device
#from intof.Models import Device, Relsen 
import intof.Router as r
import intof.Models as m
import intof.Bridge as b

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

@app.route ('/')      
@app.route ('/menu')
def home ():
    return (render_template('menu.html'))
    
# unit tests and API documentation
@app.route('/test', methods =['GET']) 
def test (): 
    b.bridge_test_method()
    return (render_template('tester.html'))
    
# buttons to control a real device            
@app.route('/buttons')
def rooot():
    return render_template ('buttons.html') 
   
@app.route('/random', methods =['GET']) 
def random (): 
    return ({'random' : randint(0, 10000)})
            
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
    
            
#-------------------------------------------------------------------------------------- 
# Add Test data
#-------------------------------------------------------------------------------------- 

@app.route('/add/minimal/data') 
def add_minimal_data():
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
    DEV1 = 'AA12345'
    DEV2 = 'BB45678'
    DEV3 = 'CC67890'  
    DEV4 = 'labs1'
    
    # TODO: all the following calls return False if they fail. Handle it!
    # device
    r.insert_device (device_id=DEV1, fallback_id='fb_DVES0BC870', mac='A2390BC870', ip='192.168.0.2',
                hardware_type="Generic", num_relays=1, num_sensors=1, enabled=True)
    r.insert_device (device_id=DEV2, fallback_id='fb_DVESBC8991', mac='B9034BC8991', ip='192.168.0.3',
                hardware_type="RND.MCU.AL2", num_relays=2, num_sensors=1, enabled=False)
    r.insert_device (device_id=DEV3, fallback_id='fb_DVES9021A8', mac='C0B5E59021A8', ip='192.168.0.4',
                hardware_type="Generic", num_relays=4, num_sensors=0, enabled=True)
    r.insert_device (device_id=DEV4, fallback_id='fb_DVES0C45A1', mac='FF34E0C45A1', ip='192.168.0.5',
                hardware_type="MCU.4.PIR.RAD.2R", num_relays=4, num_sensors=1, enabled=True)                
                
    # relsen
    sched1 = json.dumps({"schedule":[[6.30,7.0],[18.0,19.20]]})
    sched2 = json.dumps({"schedule":[[11.0,12.0],[13.0,14.50]]})
    sched3 = json.dumps({"schedule":[[10.0,15.10]]})
    sched4 = json.dumps({"schedule":[[9.0,12.0],[12.10,12.40],[16.0,18.30]]})

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
    
# Simulate an onboarding operation    
@app.route('/simul/onboard/device') 
def simul_onboard_device():    
    jnew_device = {'device_id' : 'LatestDevice', 'relsen_list' : ['Relay1', 'Relay2', 'Sensor']}
    if r.onboard_device (jnew_device):
        return {'result' : 'device onboarded successfully'}
    return {'error' : 'failed to onboard device'}

# Simulate bulk onboarding operation    
@app.route('/simul/bulk/onboard') 
def simul_bulk_onboard():    
    jnew_devices = {'NewDevice1': ['Rel1', 'Rel2'], 'NewDevice2': ['Relay8'], 'NewDevice3': ['Rels1', 'Rels2', 'Sensor1']}
    if r.bulk_onboard_devices (jnew_devices):
        return {'result' : 'all devices onboarded successfully'}
    return {'error' : 'failed to onboard at least one device'}
    
# Simulate an update_device operation    
@app.route('/simul/update/device') 
def simul_update_device():
    dev = m.Device.query.filter_by (device_id='labs1').first()
    if (not dev):
        return {'error' : 'labs1 : invalid device_id'}
    en = not(dev.enabled)  # toggle the current status
    jupdate = {'device_id' : 'labs1', 'enabled' : en}
    update_device (jupdate)
    return {'result' : 'device labs1 updated'}
    
# Simulate an update_relsen operation        
@app.route('/simul/update/relsen') 
def simul_update_relsen():
    rs = m.Relsen.query.filter_by (device_id='labs1', relsen_id='POWER1').first()
    if (not rs):
        return {'error' : 'invalid device_id or relsen_id'}
    jupdate = {
        'device_id':'labs1', 'relsen_id':'POWER1',
        'relsen_name':'Table fan', 'relsen_type': 'Fan',
        'room_name':'Grandpa\'s room', 'room_type': 'Dining room', 'group_name':'Basement',
        'schedule': json.dumps({"schedule":[[10.0,11.30]]}), 
        'repeat':False
    }
    update_relsen (jupdate)
    return {'result' : 'relsen labs1.POWER1 updated'}    
        