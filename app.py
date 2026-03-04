import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mohannad_family_2026'

# رابط مونجو الخاص بك مع بياناتك المحدثة
app.config["MONGO_URI"] = "mongodb+srv://mohannad:family123@cluster0.arkrscx.mongodb.net/chat_db?retryWrites=true&w=majority&appName=Cluster0"

# تهيئة اتصال مونجو
mongo = PyMongo(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- نموذج المستخدم ---
class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']

@login_manager.user_loader
def load_user(user_id):
    user_data = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    return User(user_data) if user_data else None

# --- المسارات ---

@app.route('/')
@login_required
def index():
    # جلب آخر 50 رسالة من المجموعة
    messages = list(mongo.db.messages.find({"receiver": "Group"}).sort("timestamp", 1).limit(50))
    return render_template('chat.html', messages=messages)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_data = mongo.db.users.find_one({"username": username, "password": password})
        if user_data:
            user_obj = User(user_data)
            login_user(user_obj)
            return redirect(url_for('index'))
        else:
            return "خطأ في البيانات.. تأكد من الاسم وكلمة المرور"
    return render_template('login.html')

@app.route('/send', methods=['POST'])
@login_required
def send():
    content = request.form.get('content')
    if content:
        mongo.db.messages.insert_one({
            "sender": current_user.username,
            "receiver": "Group",
            "content": content,
            "timestamp": datetime.now()
        })
    return redirect(url_for('index'))

# مسار خاص لك يا مهند لإضافة أفراد العائلة بسهولة
@app.route('/add_user/<name>/<pwd>')
def add_user(name, pwd):
    exists = mongo.db.users.find_one({"username": name})
    if not exists:
        mongo.db.users.insert_one({"username": name, "password": pwd})
        return f"تمت إضافة {name} بنجاح!"
    return "المستخدم موجود بالفعل"

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
