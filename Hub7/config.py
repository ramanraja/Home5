import os
        
class Config (object):
    SIMULATION_MODE = False
    APP_PORT = os.environ.get ('APP_PORT') or 5000
    TEMPLATES_AUTO_RELOAD = True    
    SQLALCHEMY_DATABASE_URI = 'sqlite:///Hub.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO= False  # enable this to see the internal queries
    SECRET_KEY = os.environ.get ('SECRET_KEY') or '!my--secret-key!'
    MQTT_BROKER_URL = 'localhost'      
    MQTT_BROKER_PORT = 1883
    MQTT_KEEPALIVE = 60  # sec
    MQTT_TLS_ENABLED = False  
    LWT_TOPIC = 'tele/+/LWT'
    SUB_TOPIC = 'stat/#'         
    PUB_PREFIX = 'cmnd'
    PUB_SUFFIX = 'POWER'       
    CLIENT_EVENT = 'client-event'
    SERVER_EVENT = 'server-event'
    ACK_EVENT = 'ACK'
    BROADCAST_DEVICE = 'tasmotas'  # this is case sensitive *
    BROADCAST_RELSEN = 'POWER0'    # gets status of all the relays in a device 
    PING_INTERVAL = 30  # daemon thread wake up interval
    DPRINT_ENABLED = True  # debug printing
    
    def dump ():   # satic method
        print ('\nConfig:') 
        print ('SIMULATION_MODE: %s' % Config.SIMULATION_MODE)     
        print ('DATABASE_URI: %s' % Config.SQLALCHEMY_DATABASE_URI)
        print ('DPRINT_ENABLED: %s' % Config.DPRINT_ENABLED)
        print ('APP_PORT: %d [%s]' %(Config.APP_PORT, type(Config.APP_PORT)))
        print ('SECRET_KEY: %s' %'*****')  # Config.SECRET_KEY)
        print ('MQTT_BROKER_URL: %s' % Config.MQTT_BROKER_URL)         
        print ('MQTT_BROKER_PORT: %s' % Config.MQTT_BROKER_PORT)         
        print ('MQTT_KEEPALIVE: %d' % Config.MQTT_KEEPALIVE)   
        print ('SUB_TOPIC: %s' % Config.SUB_TOPIC)  
        print ('PUB_PREFIX: %s' % Config.PUB_PREFIX)         
        print ('PUB_SUFFIX: %s' % Config.PUB_SUFFIX) 
        print ('CLIENT_EVENT: %s' % Config.CLIENT_EVENT)          
        print ('SERVER_EVENT: %s' % Config.SERVER_EVENT)          
        print ('ACK_EVENT: %s' % Config.ACK_EVENT)    
        print ('PING_INTERVAL: %s' % Config.PING_INTERVAL)    
        print ('BROADCAST_DEVICE: %s' % Config.BROADCAST_DEVICE)    
        print ('BROADCAST_RELSEN: %s' % Config.BROADCAST_RELSEN)
        print()        