from flask import current_app as app  
from flask import Flask, render_template, request
import json
from intof import db
from intof.HouseKeeper import dprint
##from intof.Router import current_user
from intof.Models import Device,Relsen,Status
from intof.Decorator import token_required

room_types = [
    "Hall", "Bed room", "Bath room", "Store room", "Pooja room", "Living room", "Garage", "Corridor", "Portico", "Balcony"
    ]
relsen_types = [
    "Bulb", "Tube light", "Fan", "AC", "Heater", "Cooler", "Motor", "Pump", "Water tank", "Temperature", "CO2", "Fire alarm", "Door", "Gate"
    ] 
hardware_types = [
    "NODE_MCU", "RHYDO_S4A", "RHYDO_S2A", "RHYDO_E2A", "RHYDO_E1A", "BLYNK_E2ATH", "INTOF_E2THPRL"
    ]

#----------------------------------------------------------------------------------------
# DB Housekeeping; TODO: bring them under access control
#----------------------------------------------------------------------------------------
def dbadmin_test_method():
    print ('\n--- I am the dbadmin stub ! ---\n')
     
@app.route('/create/db')
def create_test_db():
    dprint ('Deleting the old database...')
    db.drop_all()     # to avoid violating the unique value constraints        
    dprint ('Creating a test database...')
    db.create_all()       
    #return (add_test_data())
    return ({'result': 'Hub DB created'})  
      
      
@app.route('/delete/db')
@token_required
def delete_test_db (current_user):
    dprint ('{} is deleting the Hub database...'.format(current_user))
    db.drop_all()      
    return ({'result': 'Test DB removed'})


@app.route ('/remove/device')  
@token_required
def remove_device (current_user):
    devid = request.args.get('device_id')
    if (not devid):
        return ({'error' : 'device_id is required'})
    dev = Device.query.filter_by (device_id=devid).first()
    if (not dev):
        return ({'error' : 'invalid device_id'})
    dprint ('{} is removing a device record..'.format(current_user))    
    for rs in dev.relsens:
        db.session.delete(rs)
    for sta in dev.stat:
        db.session.delete(sta)    
    db.session.delete(dev)
    db.session.commit()
    return ({'result': 'Device record removed.'})
    
    
@app.route ('/remove/all/devices')  
@token_required
def remove_all_devices (current_user):
    dprint(remove_all_status()) # this is needed for dependency constraint
    dprint(remove_all_relsens())
    dprint ('{} is removing all device records...'.format(current_user))    
    devs = Device.query.all()
    dprint ('{} records found.'.format(len(devs)))
    for d in devs:
        db.session.delete(d)
    db.session.commit()
    return ({'result': 'All device records removed.'})

    
@app.route ('/remove/all/relsens') 
@token_required
def remove_all_relsens (current_user):
    dprint ('{} is removing all relays/sensors...'.format(current_user))    
    rel = Relsen.query.all()
    dprint ('{} records found.'.format(len(rel)))
    for rs in rel:
        db.session.delete(rs)
    db.session.commit()
    return ({'result': 'All relays & sensors removed.'})
            

@app.route ('/remove/all/status')
@token_required
def remove_all_status (current_user):
    dprint ('{} is removing all status data...'.format(current_user))    
    sta = Status.query.all()
    dprint ('{} records found.'.format(len(sta)))
    for s in sta:
        db.session.delete(s)
    db.session.commit()
    return ({'result': 'All status data removed.'})
    
#---------------------------------------------------------------------------------------------------
# types
#---------------------------------------------------------------------------------------------------
# Only room names, for use in drop down boxes    
@app.route('/list/room/names', methods =['GET'])      
def list_room_names():
    relsens = db.session.query(Relsen.room_name).distinct()  # a room name will be repeated for multiple relsens in that room
    retval = [] 
    for rs in relsens: 
        if (rs.room_name is None or len(rs.room_name)==0 or rs.room_name.lower()=='null'):
            continue
        retval.append (rs.room_name)  
    return ({'room_names': retval}) 
    
    
# Return a JSON of room names and types, useful for displaying on tiles on the UI
# A room name will be repeated in the record of every relsen in that room, so we need to remove duplicates
@app.route('/list/rooms', methods =['GET'])      
def list_all_rooms():  
    relsens = Relsen.query.all() # this will have lot of duplicate room names; take only the first instance in each
    retval = {} 
    for rs in relsens: 
        if (rs.room_name is None or len(rs.room_name)==0 or rs.room_name.lower()=='null'):
            continue
        if (rs.room_name not in retval):  # take only the first occurrance, hoping that a room is always associated with the same room_type
            retval[rs.room_name] = rs.room_type  
    return (retval) 
        
# Return a JSON of room names, types and the relsen count in each room
@app.route('/list/room/stats', methods =['GET'])      
def list_room_stats():  
    relsens = Relsen.query.all() # this will have many duplicate room names 
    retval = {} 
    for rs in relsens: 
        if (rs.room_name is None or len(rs.room_name)==0 or rs.room_name.lower()=='null'):
            continue
        # add only the first occurrance as the key. ASSUMPTION: a room is always associated with the same room_type in every record
        if (rs.room_name in retval):  
            retval[rs.room_name]['device_count'] += 1
        else:
            retval[rs.room_name] = {}
            retval[rs.room_name]['room_type'] = rs.room_type
            retval[rs.room_name]['device_count'] = 1
    return (retval) 
    
            
@app.route('/list/groups', methods =['GET'])  
def list_all_group_names():
    relsens = db.session.query(Relsen.group_name).distinct()
    retval = [] 
    for rs in relsens: 
        if (rs.group_name is None or len(rs.group_name)==0 or rs.group_name.lower()=='null'):
            continue
        retval.append (rs.group_name)  
    return ({'group_names': retval})     
        
@app.route('/list/room/types', methods =['GET'])  
def list_all_room_types():
    return ({'room_types': room_types}) 
    
    
@app.route('/list/hardware/types', methods =['GET'])  
def list_all_hardware_types(): 
    return ({'hardware_types': hardware_types}) 
    
    
@app.route('/list/relsen/types', methods =['GET'])  
def list_all_relsen_types():
    return ({'relsen_types': relsen_types})     
    
    
@app.route('/add/room/type', methods =['GET'])  # TODO: implement this
def add_room_type():
    rtype = request.args.get('room_type')
    if (rtype is None or len(rtype)==0):
        return ({'error' : 'room_type is required'})
    room_types.append (rtype)
    #db.session.commit()  # TODO: store in DB (what about the icon?)
    return ({'result': 'Room type added.'})
    
    
@app.route('/add/hardware/type', methods =['GET'])  # TODO: implement this  
def add_hardware_type():
    htype = request.args.get('hardware_type')
    if (htype is None or len(htype)==0):
        return ({'error' : 'hardware_type is required'})
    hardware_types.append (htype)
    #db.session.commit()  # TODO: store in DB (what about the icon?)
    return ({'result': 'Hardware type added.'})
    
    
@app.route('/add/relsen/type', methods =['GET'])   # TODO: implement this 
def add_relsen_type():
    rstype = request.args.get('relsen_type')
    if (rstype is None or len(rstype)==0):
        return ({'error' : 'relsen_type is required'})
    relsen_types.append (rstype)
    #db.session.commit()  # TODO: store in DB (what about the icon?)
    return ({'result': 'Relsen type added.'})
    
    
#-----------------------------------------------------------------------------------
# The following methods need to be implemented for any database other than SQLite
#-----------------------------------------------------------------------------------

@app.route('/ping/db', methods=['GET'])        
def ping_db():
    try:
        #retval = db.ping()
        retval = {'result' : '/ping/db stub'}
    except Exception as e:
        retval = {'error' : str(e)} 
    return (retval)       
    
    
@app.route('/disconnect/db', methods=['GET'])        
def disconnect_db():
    try:
        #retval = db.close()
        retval = {'result' : '/disconnect/db stub'}        
    except Exception as e:
        retval = {'error' : str(e)} 
    return (retval)   
        
    
@app.route('/reconnect/db', methods=['GET'])        
def reconnect_db():
    try:
        #retval = db.reconnect()
        retval = {'result' : '/reconnect/db stub'}        
    except Exception as e:
        retval = {'error' : str(e)} 
    return (retval) 