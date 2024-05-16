from flask import Flask, render_template, request, send_from_directory, redirect, url_for, session, flash, jsonify
app = Flask(__name__, template_folder='website/template', static_folder='website/static')
app.secret_key = 'pwd'
from database import query_database, init_database
import random

init_database(app)

##################################### Multi-relation Query with #####################################
# 1. At least two of the five queries should deal with data from more than one table, i.e., 
#    you should use at least two multirelation queries              [2/2]
# 2. You should make use of SQL JOIN                                [1/1]
# 3. You should make use of Aggregation and/or Grouping             [1/1]
# 4. You should make use of at least two of the following:          
#     a. Triggers                                                   [1/1]
#     b. Procedures                                                 [1/1]
#     c. Funcitons                                                  [1/1]


#--------------------------------------------------- Routes ---------------------------------------------------

@app.route("/")
def home():
    return send_from_directory('website/static', "home.html")

@app.route("/players")
def players():
    return render_template("players.html", users=query_database("SELECT * FROM players"))

@app.route('/<path:filename>', methods=['GET'])
def serve_static_html(filename):
    print("FILENAME: ", filename)
    if filename == "":
        return send_from_directory('website/static', "home.html")
    return send_from_directory('website/static', filename + ".html")

@app.route('/book', methods=['GET'])
def book():
    # PERHAPS CHANGE TO PROCEDURE IN CASE NEED
    club_id = request.args.get('club_id')
    if club_id is None:
        club_id = session.get("club_id")
    else:
        session["club_id"] = club_id
    golf_id = session.get('golf_id')
    date = request.args.get('booking_date')
    club_name = query_database("SELECT club_name FROM courses WHERE club_id = ?", [club_id], one=True)
    available_times = ['08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00']
    # Fetch previous bookings for the selected course and the logged-in user
    previous_bookings = []
    if date:
        previous_bookings = query_database("SELECT bookings.booking_id, bookings.tee_time, bookings.date, bookings.number_of_players FROM bookings where bookings.date = ? AND bookings.club_id = ? ORDER BY bookings.tee_time", [date, club_id])
        previous_bookings = [dict(row) for row in previous_bookings]
    return render_template('book.html', club_id = club_id,club_name=club_name["club_name"], golf_id=golf_id, available_times=available_times, previous_bookings=previous_bookings, date=date)

@app.route('/book', methods=['POST'])
def book_create():
    club_id = session.get("club_id")
    golf_id = request.form['golf_id']
    session["club_id"] = club_id
    date = request.form['booking_date']
    number_of_players = request.form['number_of_players']
    tee_time = request.form['booking_time']

    try:
        query_database("INSERT INTO bookings(club_id, golf_id, number_of_players, date, tee_time) VALUES(?, ?, ?, ?, ?)", [club_id, golf_id, number_of_players, date, tee_time], commit=True)
        calculate_greenfee(golf_id, club_id,number_of_players)
        session.pop("club_id", None)
        session["booking_id"] = query_database("SELECT last_insert_rowid()", one=True)['last_insert_rowid()']
        return redirect(url_for('booking_confirmation'))
    except Exception as e:
        flash(str(e))
        return redirect(url_for('book'))

@app.route('/booking_confirmation')
def booking_confirmation():
    booking_id = session.get("booking_id")
    booking_information = booking_confirmation_information(booking_id)
    session.pop("booking_id")
    return render_template('booking_confirmation.html', booking_details=booking_information)


@app.route('/profile')
def profile():
    golf_id = session.get('golf_id')
    club_id = request.args.get('club_id')

    # Fetch user details
    user_details = query_database("SELECT players.first_name, players.last_name, players.golf_id, players.email, players.hcp, courses.club_name FROM players JOIN membership ON players.golf_id = membership.golf_id JOIN courses ON membership.club_id = courses.club_id WHERE players.golf_id = ?", [golf_id], one=True)

    # Fetch courses for dropdown
    courses = query_database("SELECT club_id, club_name FROM courses")

    # Build the query for booking history
    query = """
        SELECT bookings.booking_id, bookings.club_id, bookings.date, bookings.tee_time, bookings.number_of_players, bookings.price, courses.club_name
        FROM bookings
        JOIN courses ON bookings.club_id = courses.club_id
        WHERE bookings.golf_id = ?
    """
    params = [golf_id]

    # If a club_id is provided, filter by it
    if club_id:
        query += " AND bookings.club_id = ?"
        params.append(club_id)

    query += " ORDER BY bookings.date DESC, bookings.tee_time ASC"
    booking_history = query_database(query, params)

    return render_template('profile.html', user=user_details, bookings=booking_history, courses=courses)

@app.route('/login', methods=['POST'])
def login():
    golf_id = request.form['golf_id']
    password = request.form['password']
    print("golf id: ", golf_id)
    print("password: ", password)
    player = query_database("SELECT * FROM players WHERE golf_id = ? and password = ?", [golf_id, password],one=True)
    print("player: ", player)
    if player:
        print("adding golf_id to session")
        session['golf_id'] = golf_id
        return redirect(url_for('profile', golf_id=golf_id))
    return redirect(url_for('login', golf_id=golf_id))

@app.route('/calculate_price', methods=['POST'])
def calculate_price():
    golf_id = request.form['golf_id']
    club_id = request.form['club_id']
    number_of_players = int(request.form['number_of_players'])
    
    green_fee = query_database("SELECT greenfee FROM courses WHERE club_id = ?", [club_id], one=True)['greenfee']
    
    # Check membership
    is_member = query_database("SELECT 1 FROM membership WHERE golf_id = ? AND club_id = ?", [golf_id, club_id], one=True)
    price = 0 if is_member else green_fee * number_of_players
    
    return jsonify({'price': price})


@app.route('/courses', methods=['GET'])
def show_courses():
    if session.get("club_id"):
        session.pop("club_id")
    golf_id = session.get('golf_id')
    user = query_database('SELECT * FROM Players WHERE golf_id = ?', [golf_id], one=True)
    courses = query_database("SELECT * FROM Courses")
    return render_template('courses.html', courses=courses, user=user)

@app.route('/register/new_user', methods=['POST'])
def register():
    birthdate_str = request.form['birthdate']
    golf_id = generate_golf_id(birthdate_str)
    password = request.form['password']
    email = request.form['email']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    hcp = random_hcp()
    query_database("INSERT INTO players(golf_id, password, email, first_name, last_name, hcp) VALUES(?, ?, ?, ?, ?, ?)", [golf_id, password, email, first_name, last_name, hcp], commit=True)
    # return send_from_directory('website/static', 'login.html')
    print("here")
    return redirect(url_for('registration_success', golf_id=golf_id))

@app.route('/register')
def register_courses():
    courses = query_database("SELECT * FROM courses")
    return render_template("register.html", courses=courses)

@app.route('/register/success/<golf_id>')
def registration_success(golf_id):
    return render_template('register_confirmation.html', golf_id=golf_id)

@app.route('/logout')
def logout():
    session.pop('golf_id', None)
    return redirect(url_for('login'))


#--------------------------------------------------- HELPER FUNCTIONS ---------------------------------------------------

def generate_golf_id(birthdate_str):
    # Generate golf_id
    # Extract year, month, and day from birthdate string
    birth_year = birthdate_str[:2]
    birth_month = birthdate_str[2:4]
    birth_day = birthdate_str[4:]

    # Count the number of users with the same birthdate
    count = query_database("SELECT COUNT(*) FROM players WHERE golf_id LIKE ?", 
                     (f"{birth_year}{birth_month}{birth_day}-%",), one=True)

    # Generate golf ID with suffix based on the count
    golf_id_suffix = count[0] + 1 if count else 1
    golf_id = f"{birth_year}{birth_month}{birth_day}-{golf_id_suffix:03d}"

    return golf_id

def random_hcp():
    return random.randint(0, 54)

#--------------------------------------------------- Stored Procedure ---------------------------------------------------
def calculate_greenfee(golf_id, club_id, number_of_players):
    # Stored Procedure
    membership = query_database("SELECT 1 FROM membership WHERE golf_id = ? AND club_id = ?", [golf_id, club_id], one=True)
    booking_id = query_database("SELECT last_insert_rowid()", one=True)['last_insert_rowid()']
    if membership:
        price = 0
    else:
        greenfee = query_database("SELECT greenfee FROM courses WHERE club_id = ?", [club_id],one=True)["greenfee"]
        print(float(greenfee))
        print(float(number_of_players))
        price = float(greenfee) * float(number_of_players)
    query_database("UPDATE bookings SET price = ? WHERE booking_id = ?", [price, booking_id], commit=True)

#--------------------------------------------------- Function ---------------------------------------------------
def booking_confirmation_information(booking_id):
    # Function
    return query_database("SELECT bookings.booking_id, bookings.date as booking_date, bookings.tee_time, bookings.number_of_players, bookings.price as Price_per_person, courses.club_name,players.first_name, players.last_name, players.email FROM bookings JOIN courses ON bookings.club_id = courses.club_id JOIN players ON bookings.golf_id = players.golf_id WHERE bookings.booking_id = ?", [booking_id], one=True)


#--------------------------------------------------- Trigger ---------------------------------------------------
# CREATE TRIGGER CheckMaxPlayersBeforeBooking
# BEFORE INSERT ON bookings
# WHEN (
#     SELECT IFNULL(SUM(number_of_players), 0)
#     FROM bookings
#     WHERE date = NEW.date AND tee_time = NEW.tee_time AND club_id = NEW.club_id
# ) + NEW.number_of_players > 4
# BEGIN
#     SELECT RAISE(ABORT, 'Total players for this tee time exceeds the maximum allowed.');
# END;


if __name__ == '__main__':
    app.run(debug=True)