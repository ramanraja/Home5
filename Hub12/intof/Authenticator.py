from flask import current_app as app  
from intof.Models import User
from intof import db

import jwt
from flask import request, make_response, render_template  
from werkzeug.security import generate_password_hash, check_password_hash 
from datetime import datetime, timedelta 

TOKEN_ID = 'x-access_token'
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
        print ('email already exists: {}'.format(user))
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
    # --------- valid user; return a token: ------------------
    print ('Authenticated. generating token..')
    payload = {'email': user.email,  
               'hubid' : app.config["HUB_ID"], 
               'exp' : datetime.utcnow() + timedelta (minutes=30)} # days=30
    token = jwt.encode (payload, app.config['SECRET_KEY']).decode('UTF-8') 
    if (app.config['USE_AUTH_HEADER']==False):     # if('False') evaluates to True! ***
        resp = make_response ({'result' : 'successfully logged in.'})   
        resp.set_cookie(TOKEN_ID, token, max_age=30*60) # life time in seconds
        # Aliter: set a specific epoch for expiry
        #expiry_date = datetime.now() + timedelta (minutes=10)    # (days=30)
        #resp.set_cookie ('access_token', token,  expires=expiry_date)  
        print ('Cookie set.')
        print ("Furnish the token in a cookie 'x-access-token'")
        return (resp) 
    print ("Furnish the token in a header 'x-access-token'")
    return ({ 'user': user.name, 'token' : token}) 
    

# This is a quick and dirty login form, in case there is no real client 
@app.route('/login/form')
def login_form():
    return (render_template('login.html')) 
        
# log out
@app.route('/logout', methods =['GET']) 
def logout():
    resp = make_response ({'logout' : 'you are logged out.'})        
    resp.set_cookie(TOKEN_ID, "dummy", max_age=0) # life time=0 expires the cookie
    return (resp)  
    
    
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

      