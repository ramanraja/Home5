from flask import current_app as app  
from flask import Flask, render_template, request
import json
from intof import db
from intof.HouseKeeper import dprint
##from intof.Router import current_user
from intof.Models import Device,Relsen,Status
from intof.Decorator import token_required

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