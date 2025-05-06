import telebot
from telebot import types
import sqlite3
import json

# إنشاء اتصال بقاعدة البيانات
conn = sqlite3.connect('teams.db', check_same_thread=False)
cursor = conn.cursor()

# إنشاء جدول الفرق
cursor.execute('''
CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    creator_id INTEGER NOT NULL,
    members TEXT DEFAULT '[]'
)
''')
conn.commit()

# تهيئة البوت
bot = telebot.TeleBot("7450218161:AAGteKIsYHnaLB6vPSoWYFzJ-6XUcZjZDf8")

# دالة لإنشاء لوحة المفاتيح
def create_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("انشاء تيم"))
    markup.add(types.KeyboardButton("حذف تيم"))
    markup.add(types.KeyboardButton("انضمام لتيم"))
    markup.add(types.KeyboardButton("عرض التيمات"))
    return markup

# بدء البوت
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلا وسهلا خلي تختار من الأزرار الي تحت", reply_markup=create_main_keyboard())

# معالجة إنشاء تيم
@bot.message_handler(func=lambda message: message.text == "انشاء تيم")
def create_team_handler(message):
    msg = bot.reply_to(message, "اكتب اسم التيم الي تريد تنشئه")
    bot.register_next_step_handler(msg, process_team_name)

def process_team_name(message):
    team_name = message.text
    creator_id = message.from_user.id
    
    cursor.execute("SELECT name FROM teams WHERE name = ?", (team_name,))
    if cursor.fetchone():
        bot.reply_to(message, "هذا التيم موجود بالفعل خلي تختار اسم ثاني", reply_markup=create_main_keyboard())
        return
    
    cursor.execute("INSERT INTO teams (name, creator_id) VALUES (?, ?)", (team_name, creator_id))
    conn.commit()
    
    bot.reply_to(message, f"تم إنشاء التيم {team_name} بنجاح", reply_markup=create_main_keyboard())

# معالجة حذف تيم
@bot.message_handler(func=lambda message: message.text == "حذف تيم")
def delete_team_handler(message):
    user_id = message.from_user.id
    
    cursor.execute("SELECT name FROM teams WHERE creator_id = ?", (user_id,))
    user_teams = cursor.fetchall()
    
    if not user_teams:
        bot.reply_to(message, "ما عندك أي تيمات تنحذف", reply_markup=create_main_keyboard())
        return
    
    teams_list = "\n".join([f"- {team[0]}" for team in user_teams])
    msg = bot.reply_to(message, f"تيماتك الحالية:\n{teams_list}\n\nاكتب اسم التيم الي تريد تحذفه")
    bot.register_next_step_handler(msg, process_delete_team)

def process_delete_team(message):
    team_name = message.text
    user_id = message.from_user.id
    
    cursor.execute("SELECT creator_id FROM teams WHERE name = ?", (team_name,))
    team = cursor.fetchone()
    
    if not team:
        bot.reply_to(message, "هذا التيم ما موجود", reply_markup=create_main_keyboard())
        return
    
    if team[0] != user_id:
        bot.reply_to(message, "ما تقدر تحذف هذا التيم لأنه مو تيمك", reply_markup=create_main_keyboard())
        return
    
    cursor.execute("DELETE FROM teams WHERE name = ?", (team_name,))
    conn.commit()
    
    bot.reply_to(message, f"تم حذف التيم {team_name}", reply_markup=create_main_keyboard())

# معالجة عرض التيمات
@bot.message_handler(func=lambda message: message.text == "عرض التيمات")
def show_teams(message):
    cursor.execute("SELECT name, creator_id FROM teams")
    all_teams = cursor.fetchall()
    
    if not all_teams:
        bot.reply_to(message, "ما في تيمات مسجلة", reply_markup=create_main_keyboard())
        return
    
    response = "التيمات المتاحة:\n"
    for team in all_teams:
        creator = bot.get_chat(team[1]).first_name
        response += f"- {team[0]} (منشئه: {creator})\n"
    
    bot.reply_to(message, response, reply_markup=create_main_keyboard())

# معالجة الانضمام لتيم
@bot.message_handler(func=lambda message: message.text == "انضمام لتيم")
def join_team_handler(message):
    cursor.execute("SELECT name FROM teams")
    all_teams = cursor.fetchall()
    
    if not all_teams:
        bot.reply_to(message, "ما في تيمات متاحة للانضمام", reply_markup=create_main_keyboard())
        return
    
    teams_list = "\n".join([f"- {team[0]}" for team in all_teams])
    msg = bot.reply_to(message, f"التيمات المتاحة:\n{teams_list}\n\nاكتب اسم التيم الي تريد تنضم له")
    bot.register_next_step_handler(msg, process_join_team)

def process_join_team(message):
    team_name = message.text
    user_id = message.from_user.id
    
    cursor.execute("SELECT creator_id, members FROM teams WHERE name = ?", (team_name,))
    team = cursor.fetchone()
    
    if not team:
        bot.reply_to(message, "هذا التيم ما موجود", reply_markup=create_main_keyboard())
        return
    
    members = json.loads(team[1])
    if str(user_id) in members:
        bot.reply_to(message, "أنت منضم لهذا التيم بالفعل", reply_markup=create_main_keyboard())
        return
    
    # إرسال طلب الانضمام لمنشئ التيم
    creator_id = team[0]
    markup = types.InlineKeyboardMarkup()
    accept = types.InlineKeyboardButton("موافق", callback_data=f"accept_{user_id}_{team_name}")
    reject = types.InlineKeyboardButton("ما أوافق", callback_data=f"reject_{user_id}_{team_name}")
    markup.add(accept, reject)
    
    bot.send_message(
        creator_id,
        f"يوجد طلب انضمام للتيم {team_name} من المستخدم {message.from_user.first_name}",
        reply_markup=markup
    )
    
    bot.reply_to(message, "تم إرسال طلب انضمامك لمنشئ التيم", reply_markup=create_main_keyboard())

# معالجة ردود المنشئ
@bot.callback_query_handler(func=lambda call: True)
def handle_join_request(call):
    data = call.data.split('_')
    action = data[0]
    user_id = int(data[1])
    team_name = data[2]
    
    if action == "accept":
        cursor.execute("SELECT members FROM teams WHERE name = ?", (team_name,))
        members = json.loads(cursor.fetchone()[0])
        members.append(str(user_id))
        
        cursor.execute("UPDATE teams SET members = ? WHERE name = ?", (json.dumps(members), team_name))
        conn.commit()
        
        bot.send_message(user_id, f"تم قبول طلب انضمامك للتيم {team_name}")
        bot.answer_callback_query(call.id, "تم قبول الطلب")
        
    elif action == "reject":
        bot.send_message(user_id, f"تم رفض طلب انضمامك للتيم {team_name}")
        bot.answer_callback_query(call.id, "تم رفض الطلب")
    
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

# تشغيل البوت
bot.infinity_polling()