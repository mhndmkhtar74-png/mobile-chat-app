import os
from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mohannad_private_2026'
app.config["MONGO_URI"] = "mongodb+srv://mohannad:family123@cluster0.arkrscx.mongodb.net/chat_db?retryWrites=true&w=majority&appName=Cluster0"

mongo = PyMongo(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']

@login_manager.user_loader
def load_user(user_id):
    try:
        user_data = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        return User(user_data) if user_data else None
    except: return None

def init_family():
    family_data = {
        "مختار امين": "m101", "عائدة مهيوب": "a102", "رحاب مختار": "r103",
        "رينا مختار": "rn104", "رفاء مختار": "rf105", "ايمن مختار": "ay106",
        "مهند مختار": "mh107", "جنات مختار": "jn108", "محمد مختار": "md109"
    }
    for name, pwd in family_data.items():
        mongo.db.users.update_one({"username": name}, {"$set": {"username": name, "password": pwd}}, upsert=True)

@app.route('/')
@login_required
def index():
    init_family()
    users = mongo.db.users.find({"username": {"$ne": current_user.username}})
    # جلب رسائل العام
    messages = list(mongo.db.messages.find({"type": "public"}).sort("timestamp", 1))
    return render_template('chat.html', users=users, messages=messages, chat_type="public")

@app.route('/private/<recipient>')
@login_required
def private_chat(recipient):
    users = mongo.db.users.find({"username": {"$ne": current_user.username}})
    # جلب الرسائل بين الشخصين فقط
    messages = list(mongo.db.messages.find({
        "type": "private",
        "$or": [
            {"sender": current_user.username, "receiver": recipient},
            {"sender": recipient, "receiver": current_user.username}
        ]
    }).sort("timestamp", 1))
    return render_template('chat.html', users=users, messages=messages, chat_type="private", recipient=recipient)

@app.route('/send', methods=['POST'])
@login_required
def send():
    content = request.form.get('content')
    chat_type = request.form.get('chat_type')
    receiver = request.form.get('receiver', 'Group')
    
    if content:
        mongo.db.messages.insert_one({
            "sender": current_user.username,
            "receiver": receiver,
            "content": content,
            "type": chat_type,
            "timestamp": datetime.now()
        })
    
    if chat_type == "private":
        return redirect(url_for('private_chat', recipient=receiver))
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_data = mongo.db.users.find_one({"username": request.form.get('username'), "password": request.form.get('password')})
        if user_data:
            login_user(User(user_data))
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
