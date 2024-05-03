from flask import Flask, render_template, request, send_from_directory
app = Flask(__name__, template_folder='website/template', static_folder='website/static')
from database import query_db, init_db

init_db(app)
@app.route("/")
def home():
    return "Hello World"

@app.route("/players")
def players():
    return render_template("players.html", users=query_db("SELECT * FROM players"))

@app.route('/<path:filename>', methods=['GET'])
def serve_static_html(filename):
    print("FILENAME: ", filename)
    if filename == "":
        return send_from_directory('website/static', "index.html")
    return send_from_directory('website/static', filename + ".html")


@app.route('/login', methods=['POST'])
def login():
    # golf_id = request.json.get('golf_id')
    # password = request.json.get('password')
    golf_id = request.form['golf_id']
    password = request.form['password']
    print("golf id: ", golf_id)
    print("password: ", password)
    player = query_db('SELECT * FROM players WHERE golf_id = ? and password = ?', [golf_id, password],one=True)
    print("user: ", player)


if __name__ == '__main__':
    app.run(debug=True)