#BDCC Project, Cohort 2

#Christopher Hoang

#This project is a web application where users can manage and pay their electric bill, as well as
#view other information. Employees can add, update, or delete bills that are charged to customers.
#Admins can manage employees, adding people to the system whenever. This application is developed
#using Python Flask. It incorporates MySQL and plugins such as Flask-Login. It is hosted on AWS
#Elastic Beanstalk and uses an RDS database.

from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from LoginForm import LoginForm
import pymysql
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
import io
import base64

#Database connection to AWS RDS instance
conn = pymysql.connect(
    host = '***',
    user = '***',
    password = '***',
    db = '***',
    autocommit=True)


#initialize application, as well as declare secret key needed for authentication
application = Flask(__name__)
application.config['TEMPLATES_AUTO_RELOAD'] = True
application.secret_key = '***'
 


#On opening the application, provide a login screen. Get the credentials then validate info
#Save a session for whether the user is logged in and ther user's email and role ID so that 
#retrieving information is easier
@application.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST' and 'password' in request.form and 'email' in request.form:
        session.pop('user', None)

        email = request.form['email']
        password = request.form['password']

        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM Users WHERE email=%s AND password=%s", (email, password))
            dbUser = cur.fetchone()
            if dbUser:
                userID = int(dbUser[0])
                cur.execute("SELECT roleID FROM UserRoles WHERE userID=%s", (userID,))
                userRole = cur.fetchone()
                session['loggedin'] = True
                session['user'] = email
                session['userID'] = userID
                session['roleID'] = userRole[0]
                return redirect(url_for('dashboard'))
            
            return redirect(url_for('login'))
                
        except Exception as e:
            print("Database connection failed due to {}".format(e))   
            
    return render_template('login.html')   


#note for pages below: I think a @login_required declarator would be necessary, but it doesn't feel
#like the login information is saved across page requests. So once can access some of these pages
#without login if you type in the URL, but I have trouble currently making sure it is wholly consistent.
#I aim to focus on core functionality, then possibly cleaning up any security or login errors

#For customers: A company about page
@application.route('/about')
def about():
    return render_template('about.html')

#For customers: A contact page if a customer has any queries or concerns
@application.route('/contact')
def contact():
    return render_template('contact.html')

#For All: A logout page
@application.route('/logout', methods=['GET'])
def logout():
    session.pop('loggedin', None)
    session.pop('user', None)
    session.pop('userID', None)
    session.pop('roleID', None)
    return redirect(url_for('home'))

#For all: a home page that shows site info
@application.route('/', methods=['GET', 'POST'])
def home():
    return render_template('index.html')


#The main dashboard that users can see when logging in. Has graphs and stats to help users
#visualize their bill data. Different pages depending on customer or employee
@application.route('/dashboard', methods=['GET'])
def dashboard():
    try:
        if 'loggedin' in session:
            #render different templates depending on if they are a customer or employee
            if session['roleID'] == 1:
                cur = conn.cursor()
                cur.execute("SELECT * FROM Users WHERE email=%s", (session['user'],))
                userinfo = cur.fetchone()

                cur = conn.cursor()
                cur.execute("SELECT * FROM Bills WHERE userID=%s", (session['userID'],))
                bills = cur.fetchall()

                #For user's bills, get the date, cost, and electricity usage in their own list
                xdate = []
                ycost = []
                yelec = []

                user_total_cost = 0
                user_total_elec = 0

                for row in bills:
                    date = row[2]
                    amount_due = row[4]
                    elec_usage = row[5]

                    user_total_cost += amount_due
                    user_total_elec += elec_usage
                    
                    xdate.append(date)
                    ycost.append(amount_due)
                    yelec.append(elec_usage)

                monthly_avg_cost = user_total_cost / len(bills)
                monthly_avg_cost = round(monthly_avg_cost, 2)
                monthly_avg_elec = user_total_elec / len(bills)
                monthly_avg_elec = round(monthly_avg_elec, 2)

                #Plot the cost and electric usage, encoding it in base64 for HTML usage
                fig = Figure()
                axis = fig.add_subplot(1, 1, 1)
                axis.set_title("Your Average Costs")
                axis.set_xlabel("Date of Monthly Bills")
                axis.set_ylabel("Monthly Costs")
                axis.grid()
                axis.plot(xdate, ycost)

                # Convert plot to PNG image
                pngImage = io.BytesIO()
                FigureCanvas(fig).print_png(pngImage)
                
                # Encode PNG image to base64 string
                pngCostImageB64String = "data:image/png;base64,"
                pngCostImageB64String += base64.b64encode(pngImage.getvalue()).decode('utf8')

                #plot for monthly average electric usage
                fig = Figure()
                axis = fig.add_subplot(1, 1, 1)
                axis.set_title("Your Average Electric Usage")
                axis.set_xlabel("Date of Monthly Bills")
                axis.set_ylabel("Monthly Electric Usage (kWh)")
                axis.grid()
                axis.plot(xdate, yelec)

                # Convert plot to PNG image
                pngImage = io.BytesIO()
                FigureCanvas(fig).print_png(pngImage)
                
                # Encode PNG image to base64 string
                pngElecImageB64String = "data:image/png;base64,"
                pngElecImageB64String += base64.b64encode(pngImage.getvalue()).decode('utf8')

                return render_template('customerIndex.html', data=userinfo, costplot=pngCostImageB64String, 
                                       elecplot=pngElecImageB64String, avg_cost=monthly_avg_cost, avg_elec=monthly_avg_elec)   
            else:
                cur = conn.cursor()
                cur.execute("SELECT * FROM Users WHERE email=%s", (session['user'],))
                userinfo = cur.fetchone()

                #Employee dashboard - get all bills
                cur = conn.cursor()
                cur.execute("SELECT * FROM Bills")
                bills = cur.fetchall()

                xdate = []
                ycost = []
                yelec = []

                total_cost = 0
                total_elec = 0
                total_unpaid = 0

                for row in bills:
                    date = row[2]
                    if row[3] == 0:
                        total_unpaid += 1
                    amount_due = row[4]
                    elec_usage = row[5]

                    total_cost += amount_due
                    total_elec += elec_usage
                    
                    xdate.append(date)
                    ycost.append(amount_due)
                    yelec.append(elec_usage)

                monthly_avg_cost = total_cost / len(bills)
                monthly_avg_cost = round(monthly_avg_cost, 2)
                monthly_avg_elec = total_elec / len(bills)
                monthly_avg_elec = round(monthly_avg_elec, 2)

                fig = Figure()
                axis = fig.add_subplot(1, 1, 1)
                axis.set_title("User Average Costs")
                axis.set_xlabel("Date of Monthly Bills")
                axis.set_ylabel("Monthly Costs")
                axis.grid()
                axis.scatter(xdate, ycost)

                # Convert plot to PNG image
                pngImage = io.BytesIO()
                FigureCanvas(fig).print_png(pngImage)
                
                # Encode PNG image to base64 string
                pngCostImageB64String = "data:image/png;base64,"
                pngCostImageB64String += base64.b64encode(pngImage.getvalue()).decode('utf8')

                #plot for monthly average electric usage
                fig = Figure()
                axis = fig.add_subplot(1, 1, 1)
                axis.set_title("User Average Electric Usage")
                axis.set_xlabel("Date of Monthly Bills")
                axis.set_ylabel("Monthly Electric Usage (kWh)")
                axis.grid()
                axis.scatter(xdate, yelec)

                # Convert plot to PNG image
                pngImage = io.BytesIO()
                FigureCanvas(fig).print_png(pngImage)
                
                # Encode PNG image to base64 string
                pngElecImageB64String = "data:image/png;base64,"
                pngElecImageB64String += base64.b64encode(pngImage.getvalue()).decode('utf8')

                return render_template('employeeIndex.html', data=userinfo, costplot=pngCostImageB64String, 
                                       elecplot=pngElecImageB64String, avg_cost=monthly_avg_cost, 
                                       total_unpaid=total_unpaid, avg_elec=monthly_avg_elec) 
        return redirect(url_for('login'))


    except Exception as e:
        print("Database connection failed due to {}".format(e))


#For customers: page to pay bills. This page shows all the user's past and current bills
@application.route('/pay-bills', methods=['GET'])
def payBills():
    try:
        if 'loggedin' in session:
            cur = conn.cursor()
            cur.execute("SELECT * FROM Bills WHERE userID=%s", (session['userID'],))
            data = cur.fetchall()

            #render different templates depending on if they are a customer or employee
            if session['roleID'] == 1:
                return render_template('paybills.html', bills=data)   
            else:
                return redirect(url_for('dashboard'))
        return redirect(url_for('login'))

    except Exception as e:
        print("Database connection failed due to {}".format(e))   


#For customers: a page where the payment transaction happens for a certain bill
@application.route('/payment/<billID>', methods=['GET', 'POST'])
def transaction(billID):
    if request.method == "POST":
        try:
            cur = conn.cursor()
            #Update the user's balance once the payment goes through, as well as marking bill as paid
            cur.execute("UPDATE Users SET balance= balance - (SELECT amountDue FROM Bills WHERE idBills=%s) WHERE idUsers=%s",
                        (billID, session['userID'],))
            cur = conn.cursor()
            cur.execute("UPDATE Bills SET isPaid=1 WHERE idBills=%s", (billID,))

            return redirect(url_for('payBills'))
        
        except Exception as e:
            print("Database connection failed due to {}".format(e))

    try:
        if 'loggedin' in session:
            cur = conn.cursor()
            cur.execute("SELECT * FROM Bills WHERE idBills=%s", (billID,))
            billinfo = cur.fetchone()

            cur = conn.cursor()
            cur.execute("SELECT balance FROM Users WHERE idUsers=%s", (session['userID'],))
            balance = cur.fetchone()

            if session['roleID'] == 1:
                return render_template('transaction.html', billinfo=billinfo, balance=balance)  
            else:
                return redirect(url_for('dashboard'))
        return redirect(url_for('login'))
    
    except Exception as e:
        print("Database connection failed due to {}".format(e))  

    
#For employees: A page that shows a customer's bills. Has a dragdown where the employee can obtain specific user's bills.
@application.route('/manage-customers-bills', methods=['GET', 'POST'])
def manageCustomerBills():    
    #POST: Once the ID in the dragdown is submitted, retrieve bills for that ID
    if request.method == "POST":
        try:
            if 'loggedin' in session:
                userID = request.form.get("CustomerList")
                cur = conn.cursor()
                cur.execute("SELECT * FROM Bills WHERE userID=%s", (userID,))
                data = cur.fetchall()

                return render_template('manageCustomerBills.html', customerBills=data, userID=userID)  
            
            return redirect(url_for('login'))

        except Exception as e:
            print("Database connection failed due to {}".format(e))   

    #GET: show page that has a dragdown of each user's ID
    try:
        if 'loggedin' in session:
            cur = conn.cursor()
            cur.execute("SELECT Users.idUsers FROM Users, UserRoles WHERE Users.idUsers=UserRoles.userID AND roleID=1")
            data = cur.fetchall()

            #render different templates depending on if they are a customer or employee
            if session['roleID'] == 2 or session['roleID'] == 3:
                return render_template('manageCustomerBills.html', customerIDs=data)   
            else:
                return redirect(url_for('dashboard'))
        return redirect(url_for('login'))

    except Exception as e:
        print("Database connection failed due to {}".format(e))    

#For employee: Using the HTML form, get all that information and add a new customer bill
@application.route("/add-customer-bill", methods=['GET', 'POST'])
def addCustomerBill():
    if request.method == 'POST':
        try:
            customer = request.form.get("InputCustomer")
            due_date = request.form.get("InputDueDate")
            amount_due = request.form.get("InputAmountDue")
            usage = request.form.get("InputElecUsage")
            is_paid = request.form.get("inputPaid")
            is_paid_int = -1
            if is_paid == "Yes":
                is_paid_int = 1
            elif is_paid == "No":
                is_paid_int = 0

            cur = conn.cursor()
            cur.execute("INSERT INTO Bills (userID, dueDate, isPaid, amountDue, kwh) VALUES (%s, %s, %s, %s, %s)", (customer, due_date, is_paid_int, amount_due, usage,))
            return redirect(url_for('manageCustomerBills'))
        
        except Exception as e:
            print("Database connection failed due to {}".format(e)) 

    try:
        if 'loggedin' in session:
            cur = conn.cursor()
            cur.execute("SELECT Users.* FROM Users, UserRoles WHERE Users.idUsers=UserRoles.userID AND roleID=1")
            data = cur.fetchall()

            if session['roleID'] == 2 or session['roleID'] == 3:
                return render_template('addCustomerBill.html', customers=data)   
            else:
                return redirect(url_for('dashboard'))
        return redirect(url_for('login'))
    
    except Exception as e:
        print("Database connection failed due to {}".format(e))  

#For employees: edit a customer bill with a particular ID when clicked. Uses form to update information
@application.route("/edit-customer-bills/<billID>", methods=['GET', 'POST'])
def editCustomerBills(billID):
    if request.method == 'POST':
        try:
            due_date = request.form.get("InputDueDate")
            is_paid = request.form.get("inputPaid")
            amount = request.form.get("InputAmountDue")
            usage = request.form.get("InputElecUsage")
            is_paid_int = -1
            if is_paid == "Yes":
                is_paid_int = 1
            elif is_paid == "No":
                is_paid_int = 0

            cur = conn.cursor()
            cur.execute("UPDATE Bills SET dueDate=%s, isPaid=%s, amountDue=%s, kwh=%s WHERE idBills=%s", (due_date, is_paid_int, amount, usage, billID,))
            return redirect(url_for('manageCustomerBills')) 
        
        except Exception as e:
            print("Database connection failed due to {}".format(e))   


    if 'loggedin' in session:
        if session['roleID'] == 2 or session['roleID'] == 3:
            return render_template('updateCustomerBills.html')   
        else:
            return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

#For employee: deletes a particular electric bill given the ID
@application.route("/delete-customer-bills/<billID>", methods=['GET', 'POST'])
def deleteCustomerBills(billID):
    if request.method == "POST":
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM Bills WHERE idBills=%s", (billID,))
            return redirect(url_for('manageCustomerBills'))
        
        except Exception as e:
            print("Database connection failed due to {}".format(e))
   
    #get method
    if 'loggedin' in session:
        if session['roleID'] == 2 or session['roleID'] == 3:
            return render_template("deleteCustomerBill.html") 
        else:
            return redirect(url_for('dashboard'))
    return redirect(url_for('login'))
  

#For employee: page that returns list of customers and options to update or delete
@application.route('/manage-customers', methods=['GET'])
def manageCustomer():
    try:
        if 'loggedin' in session:
            cur = conn.cursor()
            cur.execute("SELECT Users.* FROM Users, UserRoles WHERE Users.idUsers=UserRoles.userID AND roleID=1")
            data = cur.fetchall()

            #render different templates depending on if they are a customer or employee
            if session['roleID'] == 2 or session['roleID'] == 3:
                return render_template('manageCustomers.html', customers=data)   
            else:
                return redirect(url_for('dashboard'))
        return redirect(url_for('login'))

    except Exception as e:
        print("Database connection failed due to {}".format(e)) 

#For employee: edit a particular customer's information. This is moreso if a customer has trouble updating their info
#and needs an employee to help
@application.route("/edit-customers/<userID>", methods=['GET', 'POST'])
def editCustomer(userID):
    if request.method == "POST":
        try:
            name = request.form.get("InputName")
            email = request.form.get("InputEmail")
            address = request.form.get("InputAddress")
            phone = request.form.get("InputPhone")
            balance = request.form.get("InputBalance")

            cur = conn.cursor()
            cur.execute("UPDATE Users SET name=%s, email=%s, address=%s, phoneNumber=%s," + 
                         "balance=%s WHERE idUsers=%s", (name, email, address, phone, balance, userID,))
            return redirect(url_for('manageCustomer')) 
        
        except Exception as e:
            print("Database connection failed due to {}".format(e))   

    #Get method, gets user info to send to frontend to have already filled in form
    try:
        if 'loggedin' in session:
            cur = conn.cursor()
            cur.execute("SELECT * FROM Users WHERE idUsers=%s", (userID,))
            row = cur.fetchone()

            #render different templates depending on if they are a customer or employee
            if session['roleID'] == 2 or session['roleID'] == 3:
                return render_template('updateCustomer.html', user=row)   
            else:
                return redirect(url_for('dashboard'))
        return redirect(url_for('login'))


    except Exception as e:
        print("Database connection failed due to {}".format(e))  

#For employee: delete a particular customer from the database and system
@application.route("/delete-customers/<userID>", methods=['GET', 'POST'])
def deleteCustomer(userID):
    if request.method == "POST":
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM Users WHERE idUsers=%s", (userID,))
            return redirect(url_for('manageCustomer'))
        
        except Exception as e:
            print("Database connection failed due to {}".format(e))
   
    #get method
    if 'loggedin' in session:
        if session['roleID'] == 2 or session['roleID'] == 3:
            return render_template("deleteCustomer.html")
        else:
            return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


#For admin: Manage the other regular employees. This page returns a list of all current employees
@application.route('/manage-employees', methods=['GET'])
def manageEmployee():
    try:
        if 'loggedin' in session:
            cur = conn.cursor()
            cur.execute("SELECT Users.* FROM Users, UserRoles WHERE Users.idUsers=UserRoles.userID AND roleID = 2")
            data = cur.fetchall()

            #render different templates depending on if they are a customer or employee
            if session['roleID'] == 3:
                return render_template('manageEmployees.html', employees=data)   
            else:
                return redirect(url_for('dashboard'))
        return redirect(url_for('login'))

    except Exception as e:
        print("Database connection failed due to {}".format(e)) 


#For admin: Adds a regular employee to the system and database. Has to add a UserRole as employee since User and 
#UserRole are linked tables, and the user must be assigned as an employee
@application.route("/add-employee", methods=['GET', 'POST'])
def addEmployee():
    if request.method == 'POST':
        try:
            name = request.form.get("InputName")
            email = request.form.get("InputEmail")
            password = request.form.get("InputPassword")
            address = request.form.get("InputAddress")
            phone = request.form.get("InputPhone")
            role = request.form.get("InputRole")

            cur = conn.cursor()
            cur.execute("INSERT INTO Users (name, email, address, phoneNumber, password) VALUES (%s, %s, %s, %s, %s)",
                        (name, email, address, phone, password,))
            
            cur = conn.cursor()
            cur.execute("SELECT idUsers FROM Users WHERE email=%s", (email,))
            data = cur.fetchone()

            cur = conn.cursor()
            cur.execute("INSERT INTO UserRoles (roleID, userID) VALUES (%s, %s)", (role, data[0]))
            return redirect(url_for('manageEmployee'))
        
        except Exception as e:
            print("Database connection failed due to {}".format(e)) 

    if 'loggedin' in session:
        #render different templates depending on if they are a customer or employee
        if session['roleID'] == 3:
            return render_template('addEmployee.html')   
        else:
            return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

#For admin: edit a particular employee
@application.route("/edit-employees/<userID>", methods=['GET', 'POST'])
def editEmployee(userID):
    if request.method == "POST":
        try:
            name = request.form.get("InputName")
            email = request.form.get("InputEmail")
            address = request.form.get("InputAddress")
            phone = request.form.get("InputPhone")
            role = request.form.get("InputRole")

            cur = conn.cursor()
            cur.execute("UPDATE Users, UserRoles SET name=%s, email=%s, address=%s, phoneNumber=%s," + 
                         "roleID=%s WHERE Users.idUsers=%s AND UserRoles.userID=%s", (name, email, address, phone, role, userID, userID,))
            return redirect(url_for('manageEmployee')) 
        
        except Exception as e:
            print("Database connection failed due to {}".format(e))   

    #Get method, gets user info to send to frontend to have already filled in form
    try:
        if 'loggedin' in session:
            cur = conn.cursor()
            cur.execute("SELECT * FROM Users WHERE idUsers=%s", (userID,))
            row = cur.fetchone()

            #render different templates depending on if they are a customer or employee
            if session['roleID'] == 3:
                return render_template('updateEmployee.html', user=row)   
            else:
                return redirect(url_for('dashboard'))
        return redirect(url_for('login'))


    except Exception as e:
        print("Database connection failed due to {}".format(e))  


#For admin: delete a particular employee
@application.route("/delete-employees/<userID>", methods=['GET', 'POST'])
def deleteEmployee(userID):
    if request.method == "POST":
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM Users WHERE idUsers=%s", (userID,))
            return redirect(url_for('manageEmployee'))
        
        except Exception as e:
            print("Database connection failed due to {}".format(e))
   
    #get method
    if 'loggedin' in session:
        if session['roleID'] == 3:
            return render_template("deleteEmployee.html")
        else:
            return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


#For all: Update a user's profile information. They can update their name, email, etc. as well as add to their balance
@application.route("/profile", methods=['GET', 'POST'])
def updateProfile():
    if request.method == "POST":
        try:
            name = request.form.get("InputName")
            email = request.form.get("InputEmail")
            address = request.form.get("InputAddress")
            phone = request.form.get("InputPhone")
            balance = request.form.get("InputBalance")

            cur = conn.cursor()
            cur.execute("UPDATE Users SET name=%s, email=%s, address=%s, phoneNumber=%s," + 
                        "balance=balance + %s WHERE idUsers=%s", (name, email, address, phone, balance, session['userID'],))
            return redirect(url_for('updateProfile')) 
        
        except Exception as e:
            print("Database connection failed due to {}".format(e))   

    #Get method, gets user info to send to frontend to have already filled in form
    try:
        if 'loggedin' in session:
            cur = conn.cursor()
            cur.execute("SELECT * FROM Users WHERE idUsers=%s", (session['userID'],))
            row = cur.fetchone()

            #render different templates depending on if they are a customer or employee
            return render_template("updateUserProfile.html", user=row, roleID=session['roleID'])
        return redirect(url_for('login'))
    
    except Exception as e:
        print("Database connection failed due to {}".format(e))  

#For all: a secondary page to the profile where users can change their password. Must correctly type in their old password
#as well as their new password and confirming that new password
@application.route("/change-password", methods=['GET', 'POST'])
def updatePassword():
    if request.method == "POST":
        try:
            old_password = request.form.get("InputCurrentPassword")
            new_password = request.form.get("InputNewPassword")
            confirm_password = request.form.get("InputConfirmPassword")

            cur = conn.cursor()
            cur.execute("SELECT password FROM Users WHERE idUsers=%s", (session['userID'],))
            row = cur.fetchone()[0]

            if row == old_password and new_password == confirm_password:
                cur = conn.cursor()
                cur.execute("UPDATE Users SET password=%s WHERE idUsers=%s", (new_password, session['userID'],))
                return redirect(url_for('updateProfile'))
            else:
                return redirect(url_for('dashboard'))
        except Exception as e:
            print("Database connection failed due to {}".format(e))  

    try:
        if 'loggedin' in session:
            return render_template("updatePassword.html")

        return redirect(url_for('login'))
    
    except Exception as e:
        print("Database connection failed due to {}".format(e))  



if __name__ == "__main__":
    
    application.run(debug=True)
