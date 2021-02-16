# MQTT-Web socket bridge
# For your HTML clients, get the latest socketio client library from:
#   https://cdnjs.cloudflare.com/ajax/libs/socket.io/3.1.0/socket.io.min.js 

from flask import current_app as app  
from flask import Flask, render_template, request   #,redirect
import json
from intof import  mqtt, socketio
from time import sleep
from threading import Lock
from intof.HouseKeeper import dprint
import intof.Router as r
from intof.Router import list_all_devices

SIMULATION_MODE = app.config['SIMULATION_MODE']     #True    
DPRINT_ENABLED = app.config['DPRINT_ENABLED']       #True   

# MQTT
subscribed = False       
EMPTY_PAYLOAD = ''
SUB_TOPIC = app.config['SUB_TOPIC']                 #'stat/#'
LWT_TOPIC  = app.config['LWT_TOPIC']                # tele/+/LWT  
PUB_PREFIX = app.config['PUB_PREFIX']               #'cmnd'
PUB_SUFFIX = app.config['PUB_SUFFIX']               #'POWER'

BROADCAST_RELSEN = app.config['BROADCAST_RELSEN']   #'POWER0'     
BROADCAST_DEVICE = app.config['BROADCAST_DEVICE']   #'tasmotas'  # this is case sensitive **

SENSOR_STATUS = app.config['SENSOR_STATUS']         # 'STATUS10'
IPMAC_STATUS = app.config['IPMAC_STATUS']           # 'STATUS5'
IPMAC_SUFFIX = app.config['IPMAC_SUFFIX']           # 'status' 
IPMAC_PAYLOAD = app.config['IPMAC_PAYLOAD']         # '5'     

SENSOR_SUFFIX = app.config['SENSOR_SUFFIX']         # 'status' 
SENSOR_PAYLOAD = app.config['SENSOR_PAYLOAD']       # '10'     
SENSOR_RELSEN = app.config['SENSOR_RELSEN']         # 'SENSOR'    
SENSOR_INTERVAL = app.config['SENSOR_INTERVAL']     # 10  (5 minutes=10x30 sec ticks)

# socket
client_count = 0         
sensor_count = 0           
CLIENT_EVENT = app.config['CLIENT_EVENT']           #'client-event'    
SERVER_EVENT = app.config['SERVER_EVENT']           #'server-event'    
ACK_EVENT = app.config['ACK_EVENT']                 #'ACK'  

ON = 'ON'
OFF = 'OFF'
LWT = 'LWT'
ONLINE = 'online'
OFFLINE = 'offline'

# thread
bgthread = None
thread_lock = Lock()
TERMINATE = False  # TODO: use this in theapp.py
PING_INTERVAL = app.config['PING_INTERVAL']         # 30
MAX_RETRIES = 2   # No. of pings before declaring a device offline 
MAX_TIMERS = 4    # 2 ON and 2 OFF timers alloted per relay

# in-memory cache
in_mem_devices = None
in_mem_relsens = None
in_mem_status = None
in_mem_network = None
simul_status = None
is_online = None
new_devices = None

#--------------------------------------------------------------------------------------------
# helpers
#--------------------------------------------------------------------------------------------
def bridge_test_method():
    print ('\n--- I am the bridge stub ! ---\n')

'''
DPRINT_ENABLED = True
def dprint (*args):
    #app.logger.info (*args)
    if DPRINT_ENABLED:
        print (*args)     
'''        
#--------------------------------------------------------------------------------------------
# daemon
#--------------------------------------------------------------------------------------------

def bgtask():
    dprint ('Entering background thread...')
    sleep(5)
    global TERMINATE
    while not TERMINATE:
        socketio.sleep (PING_INTERVAL) # stop/daemon will be mostly called during this sleep
        if TERMINATE : 
            break
        #dprint ('\nWaking !...')
        for devid in is_online:
            if (not is_online[devid]['online']):  # TODO: Make 3 attempts before declaring it offline
                is_online[devid]['count'] = (is_online[devid]['count']+1) % MAX_RETRIES
                if (is_online[devid]['count']==0):
                    mark_offline (devid)
                    send_offline_notification (devid)
        for devid in is_online:
            is_online[devid]['online'] = False    # reset for next round of checking   
        send_tracer_broadcast() # get status of all relays: Necessary, when a device comes out of the offline mode
    print ('\n *** Background thread terminates. ***\n')  
          
    
@app.route('/start/daemon', methods=['GET']) 
def start_daemon():    
    global bgthread, TERMINATE
    if SIMULATION_MODE:
        dprint ('\n* In Simulation Mode: not starting daemon thread *\n')
        return
    print ('\nChecking daemon...')
    with thread_lock:
        if bgthread is None:  # as this should run only once
            print ('\nStarting background thread...\n')
            TERMINATE = False  # reset the flag -it it was earlier stopped manually 
            bgthread = socketio.start_background_task (bgtask)    
    return {'result' : 'Worker thread started.'}                      
             
             
@app.route('/stop/daemon', methods=['GET'])
def stop_daemon():
    global bgthread, TERMINATE
    print ('\n**** TERMINATING DAEMON THREAD ! ****\n')
    TERMINATE = True
    bgthread = None  # TODO: study the safety of this, if the thread is still in sleep mode
    return {'result' : 'Worker thread stopped.'}                     
    
#--------------------------------------------------------------------------------------------
# initialization
#--------------------------------------------------------------------------------------------

def initialize_all():
    print ('\n+ in the application initialization block..')
    build_device_inventory()
    build_initial_status()  # to correctly light the buttons initially
    start_daemon()
    #sleep(5)  # this does not help delay the MQTT subsciption
    subscribe_mqtt() # subscribing here is a safety net

    
def subscribe_mqtt():  
    global subscribed
    if SIMULATION_MODE:
        dprint ('\n* In Simulation Mode: not subscribing to MQTT *\n')
        return
    # TODO: additional subscriptions like TELE
    # do not check the 'subscribed' flag here: this may be a reconnect event!    
    print ('Subscribing to MQTT: %s' %(SUB_TOPIC))
    mqtt.subscribe (SUB_TOPIC)     # duplicate subscriptions are OK
    print ('Subscribing to MQTT: %s' %(LWT_TOPIC))
    mqtt.subscribe (LWT_TOPIC)     # duplicate subscriptions are OK
    subscribed = True  # tell socketIO.on_connect() not to subscribe again
    
#---------- receive MQTT messages

# when a device sends an MQTT message:  
# if it is in the database and is enabled, add/update its status in the cache called in_mem_status
# if not, add/update it in the dormant devices' cache called new_devices
# also mark the device as being online in the cache called is_online
# TODO: there is too much work done in the MQTT thread here. Move it to a worker thread **
def extract_status (message):  
    global in_mem_status, is_online, new_devices
    sp = message.topic.split('/')
    #print ("Parsed: ", sp)
    devid = sp[1] 
    rsid  = sp[2]
    if (rsid == LWT):
        process_lwt (devid, message.payload.decode())
        return None  # do not process it further
    if (rsid == SENSOR_STATUS):   # STATUS10: sensor readings
        update_sensor_reading (devid, message.payload.decode()) # notify the socket client. TODO:cache it
        return None
    if (rsid == IPMAC_STATUS):   # STATUS5: IP address and MAC values of device
        update_network_params (devid, message.payload.decode())
        return None        
    if (not rsid.startswith('POWER')):      # TODO: handle other messages also
        return None
    sta = message.payload.decode()           # payload is the relay status: ON/OFF
    jstatus = {"device_id" : devid, "relsen_id" : rsid, "status" : sta}
    #dprint ('JSTATUS:', jstatus)
    if not devid in in_mem_devices:          # unregistered/ disabled device found; cache them in a separate structure
        if not devid in new_devices:         # we are hearing from this device for the first time
            new_devices[devid] = []          # create the key
        if (not rsid in new_devices[devid]): # avoid duplicate relsens!
            new_devices[devid].append(rsid)
        return None                          # do not process unregistered devices any further
    # device is in the database, is enabled, but not in the in_mem_status cache yet:
    if not devid in in_mem_status:           # this acts as device discovery
        in_mem_status[devid] = {}            # add the newly discovered device as the key
    in_mem_status[devid][rsid] = sta  
    is_online[devid]['online'] = True        # this creates the key, if not already existing
    return jstatus
    
    
def process_lwt (devid, message):    # TODO: there is too much work done in the MQTT thread here. Move it to a worker thread      
    onoff_line = message.lower()
    print ('* {} is {} !'.format(devid, onoff_line))
    if (onoff_line == OFFLINE):              # TODO: handle ONLINE case also? should we ping the device now?
        mark_offline (devid)
        send_offline_notification (devid)        
        
#---------- send MQTT messages

# ask for the sensor reading from a device        
def request_sensor_reading (device_id):  
    dprint('\nTriggering sensor reading..')      
    topic = '{}/{}/{}'.format (PUB_PREFIX, device_id, SENSOR_SUFFIX) #  cmnd/device_id/status 
    dprint (topic, SENSOR_PAYLOAD) # '10'
    mqtt.publish (topic, SENSOR_PAYLOAD)     
             
# ask for the IP address and MAC of a device        
def request_network_params (device_id):  
    dprint('\nRequesting network params..')      
    topic = '{}/{}/{}'.format (PUB_PREFIX, device_id, IPMAC_SUFFIX) #  cmnd/device_id/status 
    dprint (topic, IPMAC_PAYLOAD) # '5'
    mqtt.publish (topic, IPMAC_PAYLOAD) 
                 
# ping the first relsen of a particular device (enabled or not):
# the result will be a single response from that device.
def ping_device (device_id):
    if SIMULATION_MODE:
        dprint ('In simulation mode: not pinging the device')
        return
    dprint ('\nPinging the device: ',device_id)
    topic = '{}/{}/{}'.format (PUB_PREFIX, device_id, PUB_SUFFIX) # POWER  
    dprint (topic, ' (blank)')
    mqtt.publish (topic, EMPTY_PAYLOAD) 
    
# configure upto 4 timers (2 ON, 2 OFF) for one relay in one device
# There are 16 timers in Tasmota; so upto 4 timers per relay can be assigned, for a maximum of 4 relays
# *** ASSUMPTION: relsen_id is strictly one of the following: POWER, POWER1,POWER2,POWER3 or POWER4   ***
def update_timer (device_id, relsen_id, timer_list, repeat=True):
    dprint ('updating timer for {}/{}..'.format (device_id, relsen_id))
    relay = 1
    if (relsen_id == 'POWER'):      # the device has a single relay 
        relay = 1                   # redundant, but for clarity
    else:
        relay = relsen_id[-1]           # ASSUMPTION: relsen id is in the form POWER1, POWER2 etc. ***    
        if relay < '0' or relay > '4':  
            print ('relsen_id has to be from POWER1 to POWER4 only')
            return Flase
    relay_num = int(relay)          # relay number 1 to 4 within the device
    if len(timer_list) > 2:
        print ('\n**** CAUTION: Only 2 sechedules allowed per relay; others are ignored ****\n')
    starting_timer_id = (relay_num-1)*4 + 1
    send_timer_command (device_id, relay_num, starting_timer_id, timer_list[0], repeat)  # this sets up 2 timers: one ON, and one OFf
    if len(timer_list) > 1: # process the second pair of schedule times
        send_timer_command (device_id, relay_num, starting_timer_id+2, timer_list[1], repeat) # setup the next 2 timers
    return True

# This sets up 2 timers - one ON and one OFF timer - for a single relay
def send_timer_command (device_id, relay_num, timer_id, time_pair, repeat):
    suffix = 'Timer'+ str(timer_id)  # timer_id can be from 1 to 16
    topic = '{}/{}/{}'.format (PUB_PREFIX, device_id, suffix)
    pl = {"Enable":1,"Mode":0,"Time":time_pair[0],"Window":0,"Days":"1111111","Repeat":repeat,"Output":relay_num,"Action":1} # ON
    payload = json.dumps(pl)
    dprint (topic, payload)
    mqtt.publish (topic, payload)
    # OFF timer for the same relay:
    suffix = 'Timer'+ str(timer_id+1)
    topic = '{}/{}/{}'.format (PUB_PREFIX, device_id, suffix)
    pl = {"Enable":1,"Mode":0,"Time":time_pair[1],"Window":0,"Days":"1111111","Repeat":repeat,"Output":relay_num,"Action":0} # OFF
    payload = json.dumps(pl)
    dprint (topic, payload)
    mqtt.publish (topic, payload)

# Clear all the timers of a particular device (enabled or not):  
def clear_timers (device_id, relsen_id):
    dprint ('Clearing all timers for: {}/{}'.format (device_id, relsen_id))
    relay = 1
    if (relsen_id == 'POWER'):      # the device has a single relay 
        relay = 1                   # redundant, but for clarity
    else:
        relay = relsen_id[-1]           # ASSUMPTION: relsen id is in the form POWER1, POWER2 etc. ***    
        if relay < '0' or relay > '4':  
            print ('relsen_id has to be from POWER1 to POWER4 only')
            return False
    relay_num = int(relay)          # relay number 1 to 4 within the device
    starting_timer_id = (relay_num-1)*4 + 1    
    for i in range (0, MAX_TIMERS):
        relsen = 'Timer'+ str(starting_timer_id+i)
        topic = '{}/{}/{}'.format (PUB_PREFIX, device_id, relsen)   
        payload = json.dumps({"Enable":0})
        dprint (topic, payload)
        mqtt.publish (topic, payload)
    return True
        
# ping all relays of a particular device (enabled or not):
# this will elicit one response per every relay in that device.
def ping_relsens (device_id):
    if SIMULATION_MODE:
        dprint ('In simulation mode: not pinging the relays')
        return
    dprint ('\nPinging relsens in the device: ',device_id)
    topic = '{}/{}/{}'.format (PUB_PREFIX, device_id, BROADCAST_RELSEN)  
    mqtt.publish (topic, EMPTY_PAYLOAD) 
        
# send a probe to see which of your devices are responding
# only get the first relay's status of all devices that are online;
# (they may be in the database or not, enabled or not)  
def ping_mqtt():
    if SIMULATION_MODE:
        dprint ('In simulation mode: not pinging MQTT devices')
        return
    dprint ('\nPinging all devices...')
    topic = '{}/{}/{}'.format (PUB_PREFIX, BROADCAST_DEVICE, PUB_SUFFIX) # POWER
    #dprint (topic, ' (blank)')
    mqtt.publish (topic, EMPTY_PAYLOAD)    
                   
# send a probe to trace the status of ALL relays in ALL devices that are online; 
# (they may be in the database or not, enabled or not)                       
def send_tracer_broadcast():  
    global sensor_count
    if SIMULATION_MODE:
        dprint ('In simulation mode: not sending tracer')
        return
    topic = '{}/{}/{}'.format (PUB_PREFIX, BROADCAST_DEVICE, BROADCAST_RELSEN) # POWER0
    dprint ('Sending probe to: ',topic)
    mqtt.publish (topic, EMPTY_PAYLOAD)  # empty payload gets the relay status
    sensor_count = (sensor_count+1) % SENSOR_INTERVAL   
    if (sensor_count==0):
        request_sensor_reading(BROADCAST_DEVICE)
    
#---------- send socket io messages

def send_offline_notification (devid):
    print ('sending offline notification for: ', devid)
    for rs in in_mem_relsens[devid]:
        msg = {'device_id':devid, 'relsen_id':rs, 'status' : OFFLINE}
        socketio.emit (SERVER_EVENT, msg)
    
    
def send_simul_status():   # to start a new socket client in the correct status in simulation mode 
    if not SIMULATION_MODE:
        print ('Not in simulation mode: cannot simulate status')
        return
    #dprint ('sending simulated initial status...')
    for devid in simul_status:
        jstatus = {'device_id': devid}
        for rsid in simul_status[devid]:
            jstatus['relsen_id'] = rsid
            jstatus['status'] = simul_status[devid][rsid]
            socketio.emit (SERVER_EVENT, jstatus)


#--------------------------------------------------------------------------------------------
# Build the in-memory structures
#--------------------------------------------------------------------------------------------
# TODO: in all the below, return the json message itself in a tuple: (result,json_msg)

# read the device configs and relsen list of enabled devices from the database and cache them
def build_device_inventory():  
    global in_mem_relsens, in_mem_devices, new_devices
    try:
        new_devices = {}   # reset this data structure also: to start from scratch
        #dprint ('\nbuilding [enabled] in-memory devices..')
        in_mem_devices = r.dump_active_device_spec_tree()
        if (len(in_mem_devices) > 0): 
            print ("\nactive in-memory devices:")
            print (in_mem_devices)
        else:
            print ('Error: Could not build in-memory devices')
            return False
        #dprint ('\nbuilding [enabled] in-memory relsens..')
        in_mem_relsens = r.get_active_relsen_tree()
        if (len(in_mem_relsens) > 0):
            print ("\nactive in-memory relsens:")
            print (in_mem_relsens)
            return True
        else:
            print ('Error: Could not build in-memory relsons')
            return False
    except Exception as e:
        print ('* EXCEPTION 1: ',str(e))
    return False
    
def build_initial_status():    
    global in_mem_status, in_mem_network, simul_status, is_online
    in_mem_network = {}  # global
    in_mem_status = {}   # global
    simul_status = {}    # global
    is_online = {}       # global, outer json
    try:
        if (in_mem_devices is None or in_mem_relsens is None): # safety check
            result = build_device_inventory()
            if (not result):  # boolean for now (to be changed)
                return False
        isonlin = False
        if SIMULATION_MODE:
            isonlin = True   # simulated devices are always online!
        for devid in in_mem_devices:
            is_online[devid] = {} # inner json
            is_online[devid]['online'] = isonlin
            is_online[devid]['count'] = 0
        # make two structures corresponding to in_mem_relsens: status and simulated status
        for devid in in_mem_relsens:  # devid is the JSON key  
            in_mem_status[devid] = {}   
            in_mem_status[devid][SENSOR_RELSEN] = {} # this is an inner Json
            simul_status[devid] = {}
            for rsid in in_mem_relsens[devid]:  # iterate the list 
                in_mem_status[devid][rsid] = OFFLINE  # this value is always a string (even for sensor data)
                simul_status[devid][rsid] = OFF
        print ('initial in-memory status:')
        print (in_mem_status)
        print ('initial simulator status:')
        print (simul_status)        
        send_tracer_broadcast() # priming read of all online devices (in the database or not)
        request_sensor_reading (BROADCAST_DEVICE)
        request_network_params (BROADCAST_DEVICE)
        return True
    except Exception as e:
        print ('* EXCEPTION 2: ',str(e))
    return False
    
# When a new sensor reading is available, notify the client through the socket    
def update_sensor_reading (device_id, str_msg):  # TODO: save it in in-memory status (and later, in the database)
    #try:
    dprint ('sensor reading for: ', device_id)
    dprint (str_msg)
    jsensor = json.loads(str_msg)
    in_mem_status[devid][SENSOR_RELSEN] = jsensor['StatusSNS'] # this is stored as an inner json
    jstatus = {'device_id' : device_id, 'relsen_id' : SENSOR_RELSEN, 'status' : jsensor['StatusSNS']}
    socketio.emit (SERVER_EVENT, jstatus)
    #except Exception as e:
    #    print ('EXCEPTION: ', str(e))
    
def update_network_params (device_id, str_msg):  # TODO: save it in in-memory cache and database   
    global in_mem_network 
    print ('Network settings for: ', device_id)
    netparams = json.loads(str_msg)
    if (device_id not in in_mem_network):
        in_mem_network[device_id] = {}
    in_mem_network[device_id]['host_name'] = netparams['StatusNET']['Hostname']
    in_mem_network[device_id]['ip_address'] =  netparams['StatusNET']['IPAddress'] 
    in_mem_network[device_id]['mac_id'] =  netparams['StatusNET']['Mac']  
    #dprint (netparams)
    dprint(in_mem_network[device_id])
#--------------------------------------------------------------------------------------------
# MQTT
#--------------------------------------------------------------------------------------------
###mqtt._connect_handler = on_mqtt_connect

# *** BUG NOTE: this callback is never invoked when using socketIO server ! ***
@mqtt.on_connect()  
def on_mqtt_connect (client, userdata, flags, rc):
    print ('\n***** Connected to MQTT broker. *****\n')
    subscribe_mqtt()   

@mqtt.on_message()
def on_mqtt_message (client, userdata, message):
    try:
        jstatus = extract_status (message)
        if (jstatus is not None):                                      # TODO: should you have a costly exception setup in mqtt thread?
            socketio.emit (SERVER_EVENT, jstatus)   # move this to a worker thread
    except Exception as e:                       
        print ('* EXCEPTION 3: ', str(e))
            
#--------------------------------------------------------------------------------------------
# Socket IO
#--------------------------------------------------------------------------------------------
    
@socketio.on('connect')
def on_socket_connect ():
    global client_count
    client_count = client_count +1
    msg = 'A socket client connected. Client count: {}'.format(client_count) 
    print ('\n **', msg)    
    try:
        socketio.send (msg)
        if SIMULATION_MODE:
            send_simul_status()      # start new clients in the correct initial status
        else:
            send_tracer_broadcast()  # get initial button status for display
    except Exception as e:
        print ('* EXCEPTION 4: ', str(e))
    
    
@socketio.on('disconnect')
def on_socket_disconnect():
    global client_count
    if (client_count > 0):
        client_count = client_count-1
    else:
        print ('\n******** Oops! Client count is negative! *********\n')
    print ('A client disconnected. Active count= {}'.format(client_count))
 
 
#-----------------  Helper ---------------------------------
# the simulator parses on/off/toggle command and responds
def operate_simul_device (devid, relsid, action):
    new_status = ON
    if (action.upper()=='TOGGLE'):
        if (simul_status[devid][relsid]==ON): 
            new_status = OFF
    else:
        new_status = action.upper()  # it was 'on' or 'off' command
    simul_status[devid][relsid] = new_status
    jstatus = {'device_id' : devid, 'relsen_id' : relsid, 'status' : new_status}
    socketio.emit (SERVER_EVENT, jstatus)
#----------------- -------------------------------------------
 
@socketio.on (CLIENT_EVENT)   
def on_socket_event (payload):
    print ('command: ', payload)
    jcmd = json.loads (payload)
    try:
        socketio.emit (ACK_EVENT, jcmd)  # must be a json object, to avoid messy client side escape characters 
        topic = '{}/{}/{}'.format (PUB_PREFIX, jcmd['device_id'], jcmd['relsen_id'])
        if SIMULATION_MODE:
            operate_simul_device (jcmd['device_id'], jcmd['relsen_id'], jcmd['action'].lower())
        else:
            mqtt.publish (topic, jcmd['action'])
    except Exception as e:
        print ('* EXCEPTION 5: ', str(e))


# bridge: send any arbitrary MQTT message to any arbitrary topic
@socketio.on('message')
def on_socket_message (message):
    print ('pass-through message: ', message)
    jcmd = json.loads (message)
    try:
        mqtt.publish (jcmd.get('topic'), jcmd.get('payload'))
        socketio.emit (ACK_EVENT, jcmd)  # must be a json object, to avoid messy client side escape characters   
    except Exception as e:
        print ('* EXCEPTION 6: ', str(e))
    
#--------------------------------------------------------------------------------------------
# Flask routes
#--------------------------------------------------------------------------------------------
# a series of backup measures, in case the startup initialization fails
@app.before_first_request 
def before_first_request_func():  
    print ("\n* invoked before the first HTTP request..*")
    if (in_mem_devices is None or in_mem_relsens is None):
        build_device_inventory()
    if in_mem_status is None or is_online is None:
        build_initial_status()  
    if bgthread is None: 
        start_daemon()
    if (not subscribed):  
        subscribe_mqtt() # subscribing here is a safety net
                       
@app.route('/ping/socket', methods=['GET'])
def ping_socket():
    print ('\nPinging socket...')
    socketio.send ('Ping!')  # broadcast=True is implied
    return ({'result' : 'Ping sent to socket client'})
                
# Ping: just see which of your devices are responding
# only get the first relay status of all devices online, enabled or not          
@app.route('/ping/mqtt', methods=['GET'])  
def ping_mqtt_devices():
    ping_mqtt()
    return ({'result' : 'MQTT Ping sent to all online devices'})

# ping the first relay status of a particular device, enabled or not         
@app.route('/ping/device', methods=['GET'])  
def ping_device_route():
    devid = request.args.get('device_id')
    if (not devid):
        return ({'error' : 'device_id is required'})
    if (devid not in in_mem_relsens):
        return ({'error' : 'invalid or disabled device_id'})        
    ping_device(devid)
    return ({'result' : 'MQTT Ping sent to the device'})
    
# ping all the relay statuses of a particular device; it must be in database and enabled        
@app.route('/ping/relsens', methods=['GET'])  
def ping_relsens_route():
    devid = request.args.get('device_id')
    if (not devid):
        return ({'error' : 'device_id is required'})
    if (devid not in in_mem_relsens):
        return ({'error' : 'invalid or disabled device_id'})         
    ping_relsens(devid)
    return ({'result' : 'MQTT Ping sent to all the relays of the device'})
        
# get the status of ALL relays of all devices online, enabled or not        
@app.route('/send/tracer', methods=['GET']) # send a broadcast to syncup all devices
def send_tracer():
    print('\nsending tracer broadcast..')    
    send_tracer_broadcast()
    return ({'result' : 'tracer broadcast sent'})  
    
#----------- cache management

# download the device config and relsen list (only enabled devices) from the database and rebuild the cache
@app.route('/build/device/inventory', methods=['GET'])
def build_active_device_inventory():
    print ('\nbuilding active device inventory...')
    res = build_device_inventory()
    if not res:
        return ({'error' : 'could not build device inventory'})
    res = build_initial_status()        
    if not res:
        return ({'error' : 'could not build device status'})
    return ({'result':'successfully created in-memory devices'})
        
# just return the cached in-memory device configs (only enabled devices, and in the database)    
@app.route('/get/inmem/devices', methods=['GET'])
def get_inmem_devices():
    print('\nReturning in-memory devices..')
    if in_mem_devices is None:
        return {'error' : 'in-memory devices are not available'}
    return in_mem_devices 
    
# just return the cached in-memory relsen list (only from enabled devices, found in the database)        
@app.route('/get/inmem/relsens', methods=['GET'])
def get_inmem_relsens():
    print('\nReturning in-memory relsens..')
    if in_mem_relsens is None:
        return {'error' : 'in-memory relsens are not available'}
    return in_mem_relsens 
    
#---------- device status summary

# return the last known status (ON/OFF/offline) of all the relays of a device 
@app.route('/get/device/status', methods=['GET'])
def get_device_status():
    devid = request.args.get('device_id')
    if (not devid):
        return ({'error' : 'device_id is required'})
    if SIMULATION_MODE:
        if (devid not in simul_status):
            return ({'error' : 'invalid or disabled device_id'})  
        retval = {devid : {}}
        retval[devid] = simul_status[devid]
        return retval          
    if in_mem_status is None:
        send_tracer_broadcast()  # to build the status
        return {'error' : 'in-memory status is not available; please try again'}
    if (devid not in in_mem_status):
        return ({'error' : 'invalid or disabled device_id'})  
    retval = {devid : {}}
    retval[devid] = in_mem_status[devid]
    return retval    
    
# return the last known status (ON/OFF/offline) of a relay    
@app.route('/get/relay/status', methods=['GET'])
def get_relay_status():
    devid = request.args.get('device_id')
    if (not devid):
        return ({'error' : 'device_id is required'})
    rsid = request.args.get('relsen_id')
    if (not rsid):
        return ({'error' : 'relsen_id is required'})        
    if SIMULATION_MODE:
        if (devid not in simul_status):
            return ({'error' : 'invalid or disabled device_id'})  
        retval = {devid : {}}
        retval[devid][rsid] = simul_status[devid][rsid]
        return retval            
    if in_mem_status is None:
        send_tracer_broadcast()  # to build the status
        return {'error' : 'in-memory status is not available; please try again'}
    if (devid not in in_mem_status):
        return ({'error' : 'invalid or disabled device_id'})  
    retval = {devid : {}}
    retval[devid][rsid] = in_mem_status[devid][rsid]
    return retval
    
# return the last known status (ON/OFF/offline) of devices that are in the database and are enabled
@app.route('/dump/all/status', methods=['GET'])
def dump_all_status():
    if SIMULATION_MODE:
        print('\nReturning simulated status of registered devices..')
        return simul_status
    print('\nReturning in-memory status of registered and active devices..')
    if in_mem_status is None:
        send_tracer_broadcast()  # to build the status
        return {'error' : 'in-memory status is not available; please try again'}
    return in_mem_status 



# return the latest sensor readings of a device 
@app.route('/get/sensor/values', methods=['GET'])
def get_sensor_values():
    devid = request.args.get('device_id')
    if (not devid):
        return ({'error' : 'device_id is required'})
    if SIMULATION_MODE:
            return ({'error' : 'simulation mode'})  
    if in_mem_status is None:
        send_tracer_broadcast()  # to build the status
        return {'error' : 'in-memory status is not available; please try again'}
    if (devid not in in_mem_status):
        return ({'error' : 'invalid or disabled device_id'})  
    retval = {devid : {SENSOR_RELSEN : in_mem_status[devid][SENSOR_RELSEN]}}
    return retval
    
    
# return the last known online status [True/False] of devices that are in the database and are enabled 
@app.route('/get/online/status', methods=['GET'])
def get_online_status():
    print('\nReturning online status of registered and active devices..')
    if is_online is None:
        send_tracer_broadcast()  # to build the online status
        return {'error' : 'online status is not available; please try again'}
    return is_online 
    
#---------- send a request for sensor readings and network params  ---------------------------------------

# initiate sensor reading 
@app.route('/trigger/sensor', methods=['GET'])
def trigger_sensor_reading():
    devid = request.args.get('device_id')
    if (not devid):
        return ({'error' : 'device_id is required'})
    if SIMULATION_MODE:
        return ({'result' : 'in simulation mode'})
    request_sensor_reading (devid)   
    return ({'result' : 'triggered sensor reading'})
        
# manual update: request network parameters like IP address, MAC and gateway
@app.route('/trigger/network/params', methods=['GET'])
def trigger_network_params():
    devid = request.args.get('device_id')
    if (not devid):
        return ({'error' : 'device_id is required'})
    if SIMULATION_MODE:
        return ({'result' : 'in simulation mode'})
    request_network_params (devid) # this device id need not be present in the databse
    return ({'result' : 'requested network params'})        
        
#---------- online status filters : device level
    
# return the list of device ids that are online, found in the database and are enabled     
@app.route('/get/online/devices', methods=['GET'])   
def get_online_devices():
    print('\nReturning online devices..')
    if is_online is None:
        ping_mqtt()
        return {'error' : 'online status is not available; please try again'}
    online = []
    for devid in in_mem_status:  # only consider registered devices
        if is_online[devid]['online']:
            online.append (devid)
    return {'online_devices' : online} 
        
# return the list of device ids that are offline, found in the database and are enabled             
@app.route('/get/offline/devices', methods=['GET'])  
def get_offline_devices():
    print('\nReturning offline devices..')
    if is_online is None:  # the list is not yet created
        ping_mqtt()
        return {'error' : 'offline status is not available; please try again'}
    offline = {'offline_devices' : []}
    for devid in in_mem_status:   
        if not is_online[devid]['online']:
            offline['offline_devices'].append (devid)    
    return offline 

#---------- online status filters : relsen level

# return the partial relsen tree of devices that are online, found in the database and are enabled             
@app.route('/get/online/relsens', methods=['GET'])  
def get_online_relsens():
    print('\nReturning status of registered relsens that are online..')
    if SIMULATION_MODE:
        print('\nReturning registered relsens that are online..')
        return (simul_status) # in simulation mode every device is always online!
    print('\nReturning  registered and active relsens that are offline..')
    if in_mem_status is None:
        send_tracer_broadcast()  # to build the status
        return {'error' : 'in-memory status is not available; please try again'}
    return extract_online_relsens (in_mem_status)
                            
# return the partial relsen tree of devices that are offline, found in the database and are enabled             
@app.route('/get/offline/relsens', methods=['GET'])  
def get_offline_relsens():
    print('\nReturning registered relsens that are offline..')
    if SIMULATION_MODE:
        print('\nReturning registered relsens that are offline..')
        return ({}) # in simulation mode every device is always online!
    print('\nReturning  registered and active relsens that are offline..')
    if in_mem_status is None:
        send_tracer_broadcast()  # to build the status
        return {'error' : 'in-memory status is not available; please try again'}
    return extract_offline_relsens(in_mem_status)
    
#---------- status filters : by relay on/off status
    
# return the partial relsen tree of devices in ON status, are in the database and enabled
@app.route('/get/on/relsens', methods=['GET'])
def get_on_relsens():
    if SIMULATION_MODE:
        print('\nReturning registered relsens in simulated ON status..')
        return extract_on_relsens(simul_status)
    print('\nReturning relsens in ON state -registered and active only..')
    if in_mem_status is None:
        send_tracer_broadcast()  # to build the status
        return {'error' : 'in-memory status is not available; please try again'}
    return extract_on_relsens(in_mem_status)
                    
# return the partial relsen tree of devices in OFF status, are in the database and enabled
@app.route('/get/off/relsens', methods=['GET'])
def get_off_relsens():
    if SIMULATION_MODE:
        print('\nReturning registered relsens in simulated OFF status..')
        return extract_off_relsens(simul_status)
    print('\nReturning relsens in OFF state -registered and active only..')
    if in_mem_status is None:
        send_tracer_broadcast()  # to build the status
        return {'error' : 'in-memory status is not available; please try again'}
    return extract_off_relsens(in_mem_status)
                        
#------------ device discovery

# get the device ids of unregistered or disabled devices, that are nevertheless sending packets       
# compare this with /get/new/devices in Router  (that runs the DB filter enabled=False)  *    
@app.route('/list/discovered/device/ids', methods=['GET'])  
def list_discovered_device_ids():
    print('\nReturning the ids of new (unregistered/ disabled) devices..')
    if new_devices is None:
        return {'error' : 'new device list is not available; please try again'}
    newdev = []
    for devid in new_devices.keys():
        newdev.append (devid)    
    return {'new_devices' : newdev}
    
# get the relsen tree of unregistered or disabled devices, that are enevertheless sending packets                  
@app.route('/discover/devices', methods=['GET'])
def discover_devices():
    print('\nReturning relsen list of new (unregistered/ disabled) devices..')
    if new_devices is None:
        return {'error' : 'new device list is not available; please try again'}
    return new_devices             
  
# get the wifi SSIDs of newly added devices, running their own wifi AP              
@app.route('/discover/wifi/devices', methods=['GET'])   
@app.route('/simul/discover/wifi/devices', methods=['GET'])
def discover_wifi_devices():
    print('\nReturning (simulated) devices with WiFi APs..')  # TODO: implement this 
    new_aps = {'new-APs' : ['INTOF-12AC4C', 'INTOF_33EF01', 'INTOF_A094D8']}
    return new_aps 
      
@app.route('/get/network/address', methods=['GET'])
def get_network_address():
    devid = request.args.get('device_id')
    if (not devid):
        return ({'error' : 'device_id is required'})
    if SIMULATION_MODE:
        return ({'error' : 'in simulation mode'})  
    if in_mem_network is None:
         request_network_params (BROADCAST_DEVICE)
         return {'error' : 'in_mem_network is not available; please try again'}
    if (devid not in in_mem_network):
        return ({'error' : 'invalid device_id'})  
    return in_mem_network[devid] 

@app.route('/dump/network/info', methods=['GET'])
def dump_network_info():
    if SIMULATION_MODE:
        return ({'error' : 'in simulation mode'})  
    if in_mem_network is None:
         request_network_params (BROADCAST_DEVICE)
         return {'error' : 'in_mem_network is not available; please try again'}
    return in_mem_network
#------------------------------------------------------------------------------------------------------
# Helper methods
#------------------------------------------------------------------------------------------------------

def mark_offline (devid):
    dprint ('Marking offline: ', devid)
    for rs in in_mem_status[devid]:
        in_mem_status[devid][rs] = OFFLINE
        
def extract_on_relsens (jrelsen_tree):   # TODO: parameterize all the following calls and consolidate
    retval = {}
    for devid in jrelsen_tree.keys():
        for rsid in jrelsen_tree[devid]:
            if (jrelsen_tree[devid][rsid]==ON):
                if devid not in retval:
                    retval[devid]={}  # create the top level key first
                retval[devid][rsid]=ON
    return retval

def extract_off_relsens (jrelsen_tree):
    retval = {}
    for devid in jrelsen_tree.keys():
        for rsid in jrelsen_tree[devid]:
            if (jrelsen_tree[devid][rsid]==OFF):
                if devid not in retval:
                    retval[devid]={}  # create the top level key first
                retval[devid][rsid]=OFF
    return retval
    
def extract_online_relsens (jrelsen_tree):
    retval = {}
    for devid in jrelsen_tree.keys():
        for rsid in jrelsen_tree[devid]:
            if (jrelsen_tree[devid][rsid] != OFFLINE):
                if devid not in retval:
                    retval[devid]={}  # create the top level key first
                retval[devid][rsid] = jrelsen_tree[devid][rsid]
    return retval    
    
def extract_offline_relsens (jrelsen_tree):
    retval = {}
    for devid in jrelsen_tree.keys():
        for rsid in jrelsen_tree[devid]:
            if (jrelsen_tree[devid][rsid] == OFFLINE):
                if devid not in retval:
                    retval[devid]={}  # create the top level key first
                retval[devid][rsid]=OFFLINE
    return retval


@app.route('/clear/schedule', methods=['GET'])
def clear_timers_route():
    if SIMULATION_MODE:
        return ({'error' : 'in simulation mode'})  
    devid = request.args.get('device_id')
    if (not devid):
        return ({'error' : 'device_id is required'})
    rsid = request.args.get('relsen_id')
    if (not rsid):
        return ({'error' : 'relsen_id is required'})        
    clear_timers (devid, rsid)  # clear from Tasmota
    jrelsen = {'device_id':devid, 'relsen_id':rsid, 'schedule':[], 'repeat':False}  # [["10:10","20:20"]]
    print (jrelsen)
    res = r.update_relsen (jrelsen)  # remove from database
    print (res)
    return ({'result' : 'timer schedules of device cleared'})
    
    
    