#BDCC Project, Cohort 2

#Christopher Hoang

#This project is a web application where users can manage and pay their electric bill, as well as
#view other information. Employees can add, update, or delete bills that are charged to customers.
#Admins can manage employees, adding people to the system whenever. This application is developed
#using Python Flask. It incorporates MySQL and plugins such as Flask-Login. It is hosted on AWS
#Elastic Beanstalk and uses an RDS database.

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from LoginForm import LoginForm
import pymysql

#Database connection to AWS RDS instance
conn = pymysql.connect(
    host = '***'
    user = '***',
    password = '***',
    db = '***')


#initialize application, as well as declare secret key needed for authentication
application = Flask(__name__)
application.config['TEMPLATES_AUTO_RELOAD'] = True
application.secret_key = ':QA3-ltQ|QUv.>'


login_manager = LoginManager()
login_manager.init_app(application)


#User class necessary for Flask-Login. UserMixin provides the required methods for Flask-Login
class User(UserMixin):
    pass
    
    

#User_loader and request_loder methods; returns the appropiate User object
@login_manager.user_loader
def load_user(email):
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM Users WHERE email=%s", (email,))
        row = cur.fetchone()
        if row is not None:
            user = User()
            user.id = email
            return user
        else:
            return
        
    except Exception as e:
        print("Database connection failed due to {}".format(e))   

@login_manager.request_loader
def request_loader(request):
    email = request.form.get('email')

    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM Users WHERE email=%s", (email,))
        row = cur.fetchone()
        if row is not None:
            user = User()
            user.id = email
            return user
        else:
            return
        
    except Exception as e:
        print("Database connection failed due to {}".format(e))   
        

#On opening the application, provide a login screen. Get the credentials then validate info
#Have to fix this sometime, but a fully working login menu is not top priority. Currently gives an error
#if the email is wrong, but will login the person in as long as they provide a valid email, even if 
#the password is wrong
@application.route('/login', methods=['GET', 'POST'])
def login():
    
    form = LoginForm()

    if form.validate_on_submit():
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM Users WHERE email=%s AND password=%s", (email, password))
            dbUser = cur.fetchone()
            if len(dbUser) != 0:
                user = User()
                user.id = email
                login_user(user)
                return redirect(url_for('dashboard'))
                
        except Exception as e:
            print("Database connection failed due to {}".format(e))   
            
    return render_template('login.html', form=form)   


#note for pages below: I think a @login_required declarator would be necessary, but it doesn't feel
#like the login information is saved across page requests. So once can access some of these pages
#without login if you type in the URL, but I have trouble currently making sure it is wholly consistent.
#I aim to focus on core functionality, then possibly cleaning up any security or login errors

#For customers: A company about page
@application.route('/about')
def about():
    return render_template('about.html', current_user=current_user)

#For customers: A contact page if a customer has any queries or concerns
@application.route('/contact')
def contact():
    return render_template('contact.html', current_user=current_user)

#For All: A logout page
@application.route('/logout', methods=['GET'])
def logout():
    logout_user()
    return "You are logged out"

#For all: a home page that shows site info
@application.route('/', methods=['GET', 'POST'])
def home():
    return render_template('index.html', current_user=current_user)


#For users (later defined for different roles) The users's dashboard that is viewed once logged in
@application.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM Users WHERE email=%s", (current_user.id,))
        row = cur.fetchone()
        if row is None:
           return
             
    except Exception as e:
        print("Database connection failed due to {}".format(e))   

    return render_template('adminIndex.html', data=row)



if __name__ == "__main__":
    
    application.run(debug=True)
