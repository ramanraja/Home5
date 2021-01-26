#  decorator for verifying the JWT token 

from flask import current_app as app  
from intof.Models import User

import jwt
from flask import request
from functools import wraps 

# will accept a cookie 'x-access_token' or a header 'x-access-token',
# depending on the config item USE_AUTH_HEADER

# Send the header {x-access-token : <token>} or set a cookie with access_token=<token}
def token_required (f): 
    @wraps (f) 
    def decorated (*args, **kwargs): 
        token = None
        # jwt is passed in a cookie named access_token
        if (app.config.get('USE_AUTH_HEADER')==False):  # explictly comparing with False is safer!
            token = request.cookies.get ('x-access_token')
        else:
            # jwt is passed in a request header named x-access-token
            token = request.headers.get ('x-access-token')
        if not token: 
            return  ({'error' : 'missing security token'}, 401)
        try: 
            # decode the payload to fetch the current user
            decoded_token = jwt.decode (token, app.config.get('SECRET_KEY')) 
            print ('Decoded token: ', decoded_token)
            mail = decoded_token['email']
            current_user = User.query.filter_by (email=mail).first() 
        except Exception as e:
            print ('Exception: ', e) 
            return  ({'error' : str(e)}, 401)
        if (not current_user):    
            return  ({'error' : 'invalid or expired token'}, 401)
        # returns the current logged in user's contex to the routes 
        return f (current_user, *args, **kwargs) 
    return decorated 