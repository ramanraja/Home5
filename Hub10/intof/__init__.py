from config import Config
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO 
from flask_mqtt import Mqtt
from time import sleep
        
print ("Running Module: ", __name__)   
print ('At the top level..')
Config.dump()

print ('creating socket io...')
socketio = SocketIO () 
print ('socket object created.')
mqtt = Mqtt()
print ('mqtt object created.')
print ('creating dataabse ORM..')
db = SQLAlchemy ()
print ('database created.')

def create_my_app ():
    app = Flask (__name__)
    print ('configuring app..')     
    with app.app_context():
        app.config.from_object (Config)
        CORS (app)
        
        print ('initializing database..') 
        db.init_app (app)
        print ('database initialized.')   
        
        print ('initializing socket..') 
        socketio.init_app (app, async_mode='gevent', cors_allowed_origins="*")
        print ('socket object initialized.')     
  
        print ('initializing MQTT..') 
        abort = False
        while (not abort):
            try:
                mqtt.init_app (app)
                print ('mqtt object initialized.')
                break
            except Exception as e:
                print ('* EXCEPTION: ', str(e))
                if (app.config['SIMULATION_MODE']):
                    print ('\n*** No MQTT: in simulation mode ***\n')
                    abort = True
                sleep(5)    
  
        print ('initializing router..') 
        from . import Router     # imported within the app context
        from . import HouseKeeper
        from . import DBAdmin
        from . import Bridge
        Bridge.initialize_all()  # NOTE: this is how to run app level initialization code
        print ('initialization completed.') 
        return (app)
    
# NOTE: Router is imported within the app context ***
