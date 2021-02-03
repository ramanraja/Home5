IMPORTANT: Install gevent and gevent_websocekt before starting this program

This is an integration of Hubx and Auth1 code

New in this version: 
    enabled simulation mode, for testing
    Running it on Nginx
  
--------------------------------------------------------
Two virtual environments:
  deepsp : python 3.7.5
  intof: python 3.8.5

the client javascrip library cdnjs.cloudflare.com/ajax/libs/socket.io/ was upgraded from 1.7.3  to  3.1.0  in Hub12

--------------------------------------------------------

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
 