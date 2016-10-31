from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
from flask import Flask, render_template, redirect, request, session, flash
import pg, os
import stripe


# Stripe Keys
stripe_keys = {
  'secret_key': os.environ['SECRET_KEY'],
  'publishable_key': os.environ['PUBLISHABLE_KEY']
}

stripe.api_key = stripe_keys['secret_key']


tmp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask('grillber', template_folder=tmp_dir)

db = pg.DB(
    dbname=os.environ.get('PG_DBNAME'),
    host=os.environ.get('PG_HOST'),
    user=os.environ.get('PG_USERNAME'),
    passwd=os.environ.get('PG_PASSWORD')
)

app.secret_key = 'keyur12345'

#Homepage route
@app.route('/')
def login():
    return render_template(
    'grillber.html',
    )

#Calendar page route
@app.route('/reserve_date')
def render_date():
    return render_template(
    'reserve.html'
    )

#Login page route
@app.route('/login')
def log_in():
    return render_template(
    'login.html'
    )

#This route will delete all sessions and route to homepage
@app.route('/logout')
def logout():
    del session['email']
    del session['name']
    del session['id']
    return render_template(
    'grillber.html'
    )

#Signup page route
@app.route('/signup')
def sign_up():
    return render_template(
    'signup.html'
    )

#This is the route to submit the signup form and inserts it into the database
@app.route('/submit_signup', methods=['POST'])
def submit_signup():
    email = request.form.get('email')
    password = request.form.get('password')
    street = request.form.get('street')
    zip_code = request.form.get('zip_code')
    phone = request.form.get('phone')
    name = request.form.get('name').upper()
    db.insert('customer',
    email = email,
    password = password,
    street = street,
    zip_code = zip_code,
    phone = phone,
    name = name
    )
    return redirect('/login')

#This route checks for correct username and password from the login screen and assigns a session. Either redirects to homepage or gives flash error message and redirects back to login page.
@app.route('/submit_login', methods=['POST'])
def submit_login():
    email = request.form.get('email')
    password = request.form.get('password')
    query = db.query("Select * from customer where email=$1",email).namedresult()

    if len(query)>0:
        user = query[0]
        if (user.password == password and user.email == email):
            session['email'] = user.email
            session['name'] = user.name
            session['id'] = user.id
            return redirect('/')

    flash ("Please enter the correct email & password.")
    return redirect('/login')



#Route that returns grills based on availbility on that date
@app.route('/submit_date', methods=['POST'])
def date_submit():
    date = request.form.get('date')
    query = db.query("Select distinct on (size.size) size.size, grill.id as g_id, size.reserve_btn_display from grill inner join size on size.id = grill.size_id and grill.id not in"
"(SELECT grill.id from grill left outer join reservation on grill.id = reservation.grill_id where reservation.reserve_date = $1"
")",date).namedresult() #The inner query selects the ids of individual grills that are reserved on a specified date.  The outer query omits these results and returns distinct ids for each available grill size.
    if len(query)>0:
        return render_template(
        'reserve_grill.html',
        query = query,
        date = date
        )
    else:
        flash ("All grills are booked on this day.")
    return redirect('/reserve_date')

#Page that displays previous query as buttons for reserving grills.
@app.route('/reserve_grill')
def reserve_grill():
    return render_template(
    'reserve_grill.html'
    )

#Once somebody selects a grill to reserve by pressing the button on the previous page, it goes to Stripe for processing payment.
@app.route('/charge', methods=['POST'])
def charge():
    if('id' in session):
        grill_id = request.form.get('id')
        email = session['email']
        cust_id = session['id']
        date = request.form.get('date')
        query = db.query("select size.size,size.price from size inner join grill on size.id = grill.size_id where grill.id=$1",grill_id).namedresult()[0]
        return render_template(
        'charge.html',
        key=stripe_keys['publishable_key'],
        grill_id = grill_id,
        email = email,
        cust_id = cust_id,
        date = date,
        query = query
        )
    else:
        flash('Please login to reserve.')
        return redirect('/login')

#If Stripe processing goes through, then the grill is reserved by inserting a column in the reservation table of the database and renders the confirmation page.
@app.route('/submit_reservation',methods =['POST'])

def reserve_confirmation():
    grill_id = request.form.get('g_id')
    price = request.form.get('price')
    size = request.form.get('size')
    remarks = request.form.get('remarks')
    email = session['email']
    cust_id = session['id']
    date = request.form.get('date')
    customer = stripe.Customer.create(
        email=email,
        card=request.form['stripeToken']
        )
        # Only turn on if you want to charge an actual customer.
        # charge = stripe.Charge.create(
        #     customer=cust_id,
        #     amount=price,
        #     currency='usd',
        #     description='Rental Charge'
        # )

    db.insert('reservation',
    reserve_date = date,
    grill_id = grill_id,
    customer_id = cust_id,
    is_cancelled = False,
    is_returned = False
    )
    return render_template(
    'confirmation.html',
    date = date,
    size = size
    )

#Renders information for account holder.
@app.route('/account')
def account():
    query = db.query("select reservation.remarks,reservation.id as rid, customer.*, customer_id,reservation.reserve_date, size.size, grill.id as g_id, grill.is_rented, grill.unit_name from reservation inner join grill on reservation.grill_id = grill.id inner join size on grill.size_id = size.id inner join customer on reservation.customer_id = customer.id where reservation.is_cancelled = False and reservation.is_returned = False and reservation.reserve_date > now()::date -1 order by reservation.reserve_date").namedresult()
    if session['name'] == "OWNER" or session['name'] == "owner" or session['name'] == "Owner":
        return render_template(
        'owner_account.html',
        query= query
        )
    else:
        return render_template(
        'account.html',
        query = query
        )

#This is the route to cancel a standing reservation.  When someone cancels a reservation, the column in the reservation table is_cancelled turns to True and does not show up on the user's account page.
@app.route('/submit_cancel',methods =['POST'])
def cancel_submit():
    reservation_id = request.form.get('cancel')

    db.update('reservation',{
    'id' : reservation_id,
    'is_cancelled' : True
    } )
    flash('You have successfully cancelled your reservation')
    return redirect ('/account')

#This route turns a reserveration into a rental by clicking the button that is rendered on the HTML page.
@app.route('/submit_rental', methods=['POST'])
def submit_rental():
    is_rented = request.form.get('rent')
    remarks = request.form.get('remarks')
    grill_id = request.form.get('grill_id')
    rid = request.form.get('rid')
    rent_date = request.form.get('rent_date')


    if is_rented == "False":
        db.update('reservation',{
        'id' : rid,
        'remarks' : remarks,
        'is_returned' : False,
        'is_cancelled' : False
        })
        db.update('grill',{
            'id': grill_id,
            'is_rented': True
        })
    elif is_rented == "True":
        db.update('grill',{
            'id': grill_id,
            'is_rented': False
        })
        db.update('reservation',{
        'id' : rid,
        'remarks' : remarks,
        'is_returned' : True
        })

    return redirect('/account')

if __name__ == '__main__':
    # from gevent.wsgi import WSGIServer
    # http_server = WSGIServer(('', 5000), app)
    # http_server.serve_forever()
    app.run(debug=True)
