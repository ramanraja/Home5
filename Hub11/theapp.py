###from intof import app
from intof import create_my_app
from intof import Config
from intof import socketio, mqtt
#from intof import Router
from time import sleep
from sqlalchemy_utils.functions import database_exists

app = create_my_app()  # app factory

if __name__ == "__main__": 
    ##if (db.engine.reflection.Inspector.has_table ('user')):
    if database_exists(app.config["SQLALCHEMY_DATABASE_URI"]): 
        print ('\nHub Database exists.')
    else:
        print ('\n*** PANIC: Hub Database is missing ! ******\n')
    PORT =  app.config['APP_PORT']
    print ('Starting IoT Hub on port {}...'.format (PORT))
    # disabling reloader is important to avoid duplicate messages and loops!
    # debug must be False for security reasons
    try:
        socketio.run(app, host='0.0.0.0', port=PORT, use_reloader=False, debug=False) 
    except KeyboardInterrupt:
        print ('^C received.')
    mqtt.unsubscribe_all()
    print ('MQTT listeners unsubscribed.')
    ##router.TERMINATE = False  # circular import problem; TODO: make this global
    ###sleep (5)
    print ('\n* Main thread exits!')
        