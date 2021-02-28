Intof IoT Hub

-------------------------------------------------------------------------
If you run into CORS issues with web sockets:
In the __init__.py file, have this line:
socketio.init_app (app, async_mode='gevent', cors_allowed_origins="*")

If that does alone not work, hide that header in Nginx.conf and add a fresh Access-Control-Allow-Origin header supplied by Nginx proxy:

    # proxy the Flask-socketIO listening on 127.0.0.1:5000
    location / {
        proxy_pass http://mysocket;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_set_header Host $host;
        proxy_hide_header 'Access-Control-Allow-Origin';
        add_header 'Access-Control-Allow-Origin' '*';
    }
-------------------------------------------------------------------------

New in this version: 
    saving room_type and relsen_type lists in DB, along with the icon file names.
    new API call set/relay/status to operate a relay (just in case socket is not working)

--------------------------------------------------------------------
If the number of socket clients connecting to the server automatically keeps increasing:
   An exception occurred, most probably within buttons.html. This crashes the socket connection but it automatically
   keeps trying to reestablish the connection.
   
If you encounter the error:
AttributeError: module 'jwt' has no attribute 'encode'    
https://stackoverflow.com/questions/33198428/jwt-module-object-has-no-attribute-encode
The problem arises if you have both JWT and PyJWT installed. When doing import jwt it is importing the library 
JWT as opposed to PyJWT - the latter is the one you want for encoding. 
I did 
pip uninstall JWT 
and then 
pip uninstall PyJWT 
then finally 
pip install PyJWT.
You can also specify a version:
pip install PyJWT=1.6.4

flask-jwt insists on a particular version of jwt, namely, PyJWT==1.4.2
So I needed to do: 
pip uninstall jwt
pip uninstall PyJWT 
pip uninstall flask-jwt
pip install flask-jwt
------------------------------------------------------------------------
Installation instructions:
Install Anaconda : https://www.anaconda.com/products/individual
Install Nginx : https://www.nginx.com/
Copy all the files under Hub12 to a local folder of your choice.
Open a command prompt with *administrator privileges* and cd to your working folder.
Create a virtual environment and activate it:
  conda create -n intof
  conda activate intof
Install the dependencies (this step needs admin privilegest):
  pip install -r requirements.txt
Start the Flask server:
  python theapp.py
Open another command prompt window.  
CD to your Nginx folder. 
Start the Nginx server:
  nginx
Point your browser to the root of the web server. Fog eg:
  http://3.137.85.184:8000/
  or
  http://localhost:5000/

IMPORTANT:  You must have installed gevent and gevent_websocekt before starting this program.
--------------------------------------------------------------------------
Using Nginx :
> nginx 
> nginx -s stop
--------------------------------------------------------------------------
installed 
Two environments:
  deepsp : python 3.7.5
  intof: python 3.8.5

the client javascrip library cdnjs.cloudflare.com/ajax/libs/socket.io/ was upgraded from 1.7.3  to  3.1.0  in Hub12

Solved Issues:
client automatically connects every 10 econds, and client count keeps increasing. Afterwards starts decreasing.
simulation mode does not work;  ACK and RESP packets do not come to client. Or they arrive in a bunch.
SOLUTION: There was a bug in my javascript code for the buttons.html template: The relsen_id'SENSOR" case was not
handled in code, so the script threw exception whenever a SENSOR packet arrived. 

Issues:
socket client probably uses polling, not gevent ? polling-xhr.js is invoked repeatedly
There are security warinings about set-cookie: Says  "httponly, secure and x-content-type-options headers are missig"
Performance warning: "cache-control header is missing"

----------------------------------------------------------- 

> nginx 
> nginx -s stop

Nginx config:

worker_processes  1;

error_log  logs/error.log;

events {
    worker_connections  10;
}

http {
    sendfile        on;
    keepalive_timeout  65;
    map $http_upgrade $connection_upgrade {
        default upgrade;
        '' close;
    }
    server {
        listen  80;
        server_name  127.0.0.1;    # 3.x.x.x; for AWS
        # Flask-socketIO app
        location / {
            proxy_pass http://127.0.0.1:5000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection $connection_upgrade;
            proxy_set_header Host $host;
        }
    }
}