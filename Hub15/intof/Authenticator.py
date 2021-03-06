from flask import current_app as app  
from intof.Models import User
from intof import db

import jwt
from flask import request, make_response, render_template  
from werkzeug.security import generate_password_hash, check_password_hash 
from datetime import datetime, timedelta 

TOKEN_ID = app.config['TOKEN_ID'] 
DEFAULT_PASSWORD = 'changeme'
#----------------------------------------------------------------------------------------
# helper methods    
#----------------------------------------------------------------------------------------
DPRINT_ENABLED = True
def dprint (*args):
    #app.logger.info (*args)
    if DPRINT_ENABLED:
        print (*args)
        
    
def insert_user (email, name, password):
    # check for existing user (user name is not unique, but mail is unique)
    user = User.query.filter_by(email = email).first() 
    if user: 
        print ('email already exists: {}'.format(user))  # TODO: return this error message instead of boolean
        return False
    user = User( 
        name = name, 
        email = email, 
        password = generate_password_hash (password) 
    ) 
    db.session.add(user) 
    db.session.commit() 
    print ('Added user: {}'.format(user))
    return True    
    
    
def update_user (email, name=None, password=None):  # TODO: validate the lengths of name and password strings
    # check for existing user (mail is unique, and cannot be changed)
    user = User.query.filter_by(email = email).first() 
    if user is None: 
        print ('invalid email')  # TODO: return this error message instead of boolean
        return False
    if name is not None:
        user.name = name    
    if password is not None:
        user.password = generate_password_hash (password)           
    db.session.commit() 
    print ('Updated user: {}'.format(user))
    return True        
    
    
def reset_password (email):
    return update_user (email, name=None, password=DEFAULT_PASSWORD)    
#------------------------------------------------------------------------------------------
    
# This method processes the data POSTed by the login form; to display the form itself, call /login/form
# Furnish your mail id and password and get a token
@app.route('/login', methods =['GET', 'POST']) 
@app.route('/signin', methods =['GET', 'POST']) 
def login(): 
    if request.method == 'GET':
        return ({'error' : 'Please POST the email and password'})
    # takes either an HTML form, or json object in the HTTP POST payload 
    if (request.json):
        form = request.json   
    else:
        form = request.form 
    #dprint ('Form: ', form)
    if not form : 
        return ({'error' : 'Missing login credentials'}, 401)     
    if not form.get('email') or not form.get('password'): 
        return ({'error' : 'Missing email or password'}, 401) 
    # ------ retrieve password hash from db:-----------------    
    user = User.query.filter_by (email=form.get('email')).first() 
    print ('Checking credentials for user: {}'.format(user))
    if not user: 
        print ('Invalid email')
        resp = make_response ({'error' : 'invalid email or password'}) 
        resp.set_cookie(TOKEN_ID, "dummy", max_age=0) # life time=0 expires the cookie
        return (resp) 
    if not check_password_hash (user.password, form.get('password')): 
        print ('Incorrect password')
        resp = make_response ({'error' : 'invalid email or password'}) 
        resp.set_cookie(TOKEN_ID, "dummy", max_age=0) # life time=0 expires the cookie
        return (resp) 
    # TODO: check the user role and HUB_ID also
    # --------- valid user; return a token: ------------------
    print ('Authenticated. generating token..')
    payload = {'email': user.email,  
               'hubid' : app.config["HUB_ID"], 
               'exp' : datetime.utcnow() + timedelta (minutes=180)} # days=30}
    token = jwt.encode (payload, app.config['SECRET_KEY']).decode('UTF-8') 
    if (app.config['USE_AUTH_HEADER']==False):     # if('False') evaluates to True! ***
        resp = make_response ({'result' : 'successfully logged in.'})   
        resp.set_cookie(TOKEN_ID, token, max_age=30*60) # life time in seconds
        # Aliter: set a specific epoch for expiry
        #expiry_date = datetime.now() + timedelta (minutes=10)    # (days=30)
        #resp.set_cookie (TOKEN_ID, token,  expires=expiry_date)  
        dprint ('Cookie set.')
        print ("Furnish the token in a cookie '{}'".format(TOKEN_ID))
        return (resp) 
    # using HTTP auth header, so return the token as a response
    print ("Furnish the token in a header '{}'".format(TOKEN_ID))
    return ({ 'user': user.name, TOKEN_ID : token}) 
    

# This is a quick and dirty login form, in case there is no real client 
@app.route('/login/form')
def login_form():
    return (render_template('login.html')) 
        
# log out
@app.route('/logout', methods =['GET']) 
def logout():
    if (app.config['USE_AUTH_HEADER']==False):
        dprint ('User logged out.')
        resp = make_response ({'result' : 'you are now logged out.'})        
        resp.set_cookie(TOKEN_ID, "dummy", max_age=0) # life time=0 expires the cookie
        return (resp)  
    dprint ('User logout has to be handled at client side.')
    return ({'error' : 'You are using HTTP auth header. Please delete the auth token from the client local store.'})
    
# This is a quick and dirty registration form, in case there is no real client that can POST a form
@app.route('/registration/form')
def registration():
    return (render_template('register.html'))        
    
    
@app.route('/signup', methods =['GET','POST']) 
@app.route('/register', methods =['GET','POST']) 
def signup(): 
    if request.method == 'GET':
        return ({'error' : 'Please POST the email, user name and password in a form'})
    # make a dictionary out of POSTed data 
    if (request.json):
        form = request.json    
    else:
        form = request.form 
    if (not form):
        return ({'error' : 'email, name and password are required'}) 
    name, email = form.get('name'), form.get('email') 
    password = form.get('password') 
    if (not name or not email or not password):
        return ({'error' : 'Please fill in email, name and password'}) 
    if (len(name)==0 or len(email)==0 or len(password)==0):
        return ({'error' : 'email, name or password cannot be blank'})         
    if insert_user (email, name, password):
        return ({'result' : 'successfully registered'}) 
    else: 
        # user already exists 
        return ({'error' : 'email already registered'}) 

      
@app.route('/reset/password', methods =['GET']) 
def reset_password_route(): 
    email = request.args.get('email')
    if (not email):
        return ({'error' : 'email is required'})
    if reset_password (email):
        return ({'result' : "successfully reset the password to  'changeme'"})
    return ({'error' : 'Failed to reset password. Please check the mail id'})


# only name and password can be changed, not the email
# changing name is optional
@app.route('/update/user', methods =['GET', 'POST']) 
def update_user_route(): 
    if request.method == 'GET':
        return ({'error' : 'Please POST the email, user name and password in a form'})
    # make a dictionary out of POSTed data 
    if (request.json):
        form = request.json    
    else:
        form = request.form 
    if (not form):
        return ({'error' : 'email and password are required'}) 
    name = form.get('name')   # this can be None
    email = form.get('email') 
    password = form.get('password') 
    if (not email or not password):  # name can be left as None if you don't want to alter it
        return ({'error' : 'Please fill in email and password'}) 
    if (len(email)==0 or len(password)==0):
        return ({'error' : 'email or password cannot be blank'})         
    if update_user (email, name, password):
        return ({'result' : 'successfully modified user details'}) 
    else: 
        return ({'error' : 'invalid email'}) 
