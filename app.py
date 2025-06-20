from flask import Flask, redirect, request, render_template, url_for, send_from_directory
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from werkzeug.utils import secure_filename
from passlib.hash import sha512_crypt
from random import randint
from time import asctime
import pickle
import os

def load_database():
    if not os.path.exists("db/db.pickle"):
        return {}
    with open("db/db.pickle", "rb") as dbfile:
        return pickle.load(dbfile)

def save_database(database):
    os.makedirs('db', exist_ok=True)
    with open('db/db.pickle', 'wb') as f:
        pickle.dump(database, f)

def ensure_content_log():
    os.makedirs('db', exist_ok=True)
    os.makedirs('db/contents', exist_ok=True)
    if not os.path.exists('db/content-log.log'):
        with open('db/content-log.log', 'w') as f:
            pass

app = Flask(__name__)
app.secret_key = "nikhilisalpha966313022001"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id):
        self.id = id

    def repr(self):
        return self.id

@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    return redirect(url_for('home'))

@app.route('/home', methods=['GET', 'POST'])
@login_required
def home():
    ensure_content_log()
    content = []
    with open('db/content-log.log') as f:
        data = f.read().rstrip('\n')
        if data == '':
            content = None
        else:
            for line in data.split('\n'):
                content.append(line.split("???:???"))

    return render_template("home.html", uname=current_user.get_id().lower(), contents=content)

@app.route('/view-post/<filename>', methods=['GET'])
@login_required
def view_post(filename):
    ensure_content_log()
    post_data = None
    with open('db/content-log.log') as f:
        for line in f:
            parts = line.strip().split("???:???")
            if parts[0] == filename:
                post_data = {
                    'filename': parts[0],
                    'posted_at': parts[1],
                    'username': parts[2],
                    'caption': parts[3]
                }
                break
    
    if post_data is None:
        return redirect(url_for('home'))
        
    return render_template("view_post.html", 
                         post=post_data,
                         uname=current_user.get_id().lower())

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == "POST":
        uname = request.form['username'].lower()
        password = request.form['password']
        database = load_database()
        if uname in database and sha512_crypt.verify(password, database[uname]):
            login_user(User(uname))
            return redirect(url_for('home'))
        else:
            error = "Invalid Credentials!"

    return render_template("login.html", error=error)

@app.route('/signup/', methods=['GET', 'POST'])
def signup():
    error = None
    if request.method == "POST":
        if ' ' in request.form['username']:
            error = "Username cannot contain spaces!"
        elif request.form['password0'] != request.form['password1']:
            error = "Passwords must Match!"
        else:
            database = load_database()
            if request.form['username'].lower() in database:
                error = "User already Exists!"
            else:
                user_name = request.form['username'].lower()
                password = sha512_crypt.hash(request.form['password0'])
                database[user_name] = password
                save_database(database)
                login_user(User(user_name))
                return redirect(url_for('home'))

    return render_template("signup.html", error=error)

@app.route("/logout/")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@login_manager.user_loader
def load_user(userid):
    return User(userid)

@app.route('/chat-history/<path:path>', methods=['GET', 'POST'])
def send_log(path):
    return send_from_directory('db', 'chat-log.log')

@app.route("/post-chat/", methods=["GET", "POST"])
def post_chat():
    if request.form['chat_input'] != '':
        with open('db/chat-log.log', 'r') as f:
            prev_data = f.read()

        with open('db/chat-log.log', 'w') as f:
            f.write("""<strong>{}</strong>: {}\n<br>\n""".format(current_user.get_id().lower(),
                                                                 request.form['chat_input']) + prev_data)

    return render_template("chat-textbox.html")

@app.route('/delete-post/<filename>', methods=['POST'])
@login_required
def delete_post(filename):
    ensure_content_log()
    with open("db/content-log.log", 'r') as f:
        lines = f.readlines()
    updated_lines = []
    for line in lines:
        parts = line.strip().split("???:???")
        if parts[0] == filename and parts[2].lower() == current_user.get_id().lower():
            try:
                os.remove(os.path.join("db/contents", filename))
            except:
                pass
        else:
            updated_lines.append(line)
    with open("db/content-log.log", 'w') as f:
        f.writelines(updated_lines)
    return redirect(url_for('home'))

@app.route('/uploader/', methods=['GET', 'POST'])
def upload_file():
    ensure_content_log()
    if request.method == 'POST':
        f = request.files['meme-file']
        file_name = secure_filename(f.filename)
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'ogg'}
        if '.' not in file_name or file_name.rsplit('.', 1)[1].lower() not in allowed_extensions:
            return redirect(url_for('home'))
        f.save("db/contents/" + file_name)
        with open("db/content-log.log", 'r') as f:
            prev_data = f.read()
        with open("db/content-log.log", 'w') as f:
            f.write(file_name + "???:???" + asctime() + "???:???" + current_user.get_id() + "???:???" + request.form["caption-text"] + "\n" + prev_data)
        return redirect(url_for('home'))

@app.route('/edit-caption/<filename>', methods=['GET', 'POST'])
@login_required
def edit_caption(filename):
    ensure_content_log()
    if request.method == 'POST':
        new_caption = request.form['new_caption']
        updated_lines = []
        with open("db/content-log.log", 'r') as f:
            for line in f:
                parts = line.strip().split("???:???")
                if parts[0] == filename and parts[2].lower() == current_user.get_id().lower():
                    parts[3] = new_caption
                updated_lines.append("???:???".join(parts))
        with open("db/content-log.log", 'w') as f:
            f.write("\n".join(updated_lines) + "\n")
        return redirect(url_for('home'))
    return render_template("edit_caption.html", filename=filename)

@app.route('/scripts/<path:path>', methods=['GET', 'POST'])
def send_js(path):
    return send_from_directory('scripts', path)

@app.route('/templates/<path:path>', methods=['GET', 'POST'])
def send_html(path):
    return send_from_directory('templates', path)

@app.route('/content/<path:path>', methods=['GET', 'POST'])
def send_content(path):
    return send_from_directory('db/contents', path)

if __name__ == "__main__":
    app.run(debug=True, threaded=True, host='0.0.0.0', port=8000)
