# from flask import Flask, render_template, redirect, request, session, flash
# import pg
#
# app = Flask('app')
#
# @app.route('/')
# def login():
#
#     return render_template(
#     'grillber.html'
#     )
#
# @app.route('/submit_reservation', methods=['POST'])
# def submit_reservation():
#     shift = request.form.get('shift')
#     date = request.form.get('date')
#     size = request.form.get('size')
#
#     print "Shift : %s, Date: %s, Size: %s" % (shift,date,size)
#     return redirect('/')
#
#
#
#
#
# if __name__ == '__main__':

#     app.run(debug=True)
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
from flask import Flask, render_template, redirect, request, session, flash
import pg, os

tmp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask('Wiki', template_folder=tmp_dir)

db = pg.DB(
    dbname=os.environ.get('PG_DBNAME'),
    host=os.environ.get('PG_HOST'),
    user=os.environ.get('PG_USERNAME'),
    passwd=os.environ.get('PG_PASSWORD')
)

app.secret_key = 'keyur12345'



@app.route('/')
def login():
    return render_template(
    'grillber.html'
    )

@app.route('/reserve_date')
def render_date():
    return render_template(
    'reserve.html'
    )


@app.route('/login')
def log_in():
    return render_template(
    'login.html'
    )

@app.route('/logout')
def logout():
    del session['email']
    del session['name']
    return render_template(
    'grillber.html'
    )

@app.route('/signup')
def sign_up():
    return render_template(
    'signup.html'
    )

@app.route('/submit_signup', methods=['POST'])
def submit_signup():
    email = request.form.get('email')
    password = request.form.get('password')
    street = request.form.get('street')
    zip_code = request.form.get('zip_code')
    phone = request.form.get('phone')
    name = request.form.get('name')


    db.insert('customer',
    email = email,
    password = password,
    street = street,
    zip_code = zip_code,
    phone = phone,
    name = name
    )

    return redirect('/login')


@app.route('/submit_login', methods=['POST'])
def submit_login():
    email = request.form.get('email')
    password = request.form.get('password')
    query = db.query("Select * from customer where email=$1",email).namedresult()

    if len(query)>0:
        user = query[0]
        if user.password == password:
            session['email'] = user.email
            session['name'] = user.name
            print session['name']
            return redirect('/')
    else:
        return redirect('/login')



# @app.route('/submit_reservation', methods=['POST'])
# def submit_reservation():
#     date = request.form.get('date')
#     size = request.form.get('size')
#     query = db.query('''select grill.id from grill inner join size on size.id = grill.size_id where size.size = $1 and grill.id not in
#     (select grill.id from grill left outer join reservation on grill.id = reservation.grill_id where reservation.reserve_date = $2)''',size,date).namedresult()
#     if len(query)>0:
#         cust = db.query("select * from customer where email=$1",session[user]).namedresult()[0]
#         db.insert('reservation',
#                 reserve_date = date,
#                 customer_id = cust.id,
#                 grill_id = query[0].id
#                 )
#     else:
#         print "sorry your size is not available."
#
#     return redirect('/')


@app.route('/submit_date', methods=['POST'])
def date_submit():
    date = request.form.get('date')
    query = db.query("Select distinct(size.size),size.reserve_btn_display from grill inner join size on size.id = grill.size_id and grill.id not in"
"(SELECT grill.id from grill left outer join reservation on grill.id = reservation.grill_id where reservation.reserve_date = $1"
")",date).namedresult()
    if len(query)>0:
        return render_template(
        'reserve_grill.html',
        query = query,
        date = date
        )
    else:
        print "All grills are booked on this day."
    return redirect('/')


@app.route('/reserve_grill')
def reserve_grill():
    render_template(
    'reserve_grill.html'
    )
@app.route('/submit_reservation',methods =['POST'])
def reserve_confirmation():
    grill_size = request.form.get('size')
    email = session['email']
    cust_id = db.query("select id from customer where email=$1",email).namedresult()[0].id
    date = request.form.get('date')
    print cust_id

    

    return render_template(
    'reserve_grill.html'
    )



if __name__ == '__main__':
    app.run(debug=True)
