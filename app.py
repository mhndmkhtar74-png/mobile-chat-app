import os
from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mohannad_private_2026'

# رابط مونجو الخاص بك
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
    except:
        return None

# دالة إعداد العائلة بكلمات مرور مختلفة وحذف عمر عمار
def init_family():
    # قائمة العائلة مع كلمة مرور خاصة لكل فرد
    family_data = {
        "مختار امين": "m101",
        "عائدة مهيوب": "a102",
        "رحاب مختار": "r103",
        "رينا مختار": "rn104",
        "رفاء مختار": "rf105",
        "ايمن مختار": "ay106",
        "مهند مختار": "mh107",
        "جنات مختار": "jn108",
        "محمد مختار": "md109"
    }
    
    for name, pwd in family_data.items():
        # إذا لم يكن المستخدم موجوداً، نقوم بإضافته أو تحديث كلمة مروره
        mongo.db.users.update_one(
            {"username": name},
            {"$set": {"username": name, "password": pwd}},
            upsert=True
        )
    
    # التأكد من حذف "عمر عمار" من قاعدة البيانات إذا كان موجوداً
    mongo.db.users.delete_one({"username": "عمر عمار"})

@app.route('/')
@login_required
def index():
    messages = list(mongo.db.messages.find({"receiver": "Group"}).sort("timestamp", 1).limit(50))
    return render_template('chat.html', messages=messages)

@app.route('/login', methods=['GET', 'POST'])
def login():
    init_family() # تحديث البيانات عند كل دخول
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_data = mongo.db.users.find_one({"username": username, "password": password})
        if user_data:
            login_user(User(user_data))
            return redirect(url_for('index'))
        else:
            return "خطأ في الاسم أو كلمة المرور الخاصة بالعائلة"
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

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
