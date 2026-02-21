import telebot
from telebot import types
import sqlite3
import random
import time

# --- CẤU HÌNH ---
# CẢNH BÁO: Hãy đổi Token này trong @BotFather vì nó đã bị lộ công khai!
TOKEN = '8564750082:AAGkVvtYyRBbsD9xkAXkmiadLiE_kmk_zfs' 
bot = telebot.TeleBot(TOKEN)

# --- DATABASE LOGIC ---
def init_db():
    conn = sqlite3.connect('game_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 50000)''')
    conn.commit()
    conn.close()

def get_balance(user_id):
    conn = sqlite3.connect('game_data.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE id=?", (user_id,))
    res = c.fetchone()
    if res: return res[0]
    c.execute("INSERT INTO users (id, balance) VALUES (?, ?)", (user_id, 50000))
    conn.commit()
    return 50000

def update_balance(user_id, amount):
    new_bal = get_balance(user_id) + amount
    conn = sqlite3.connect('game_data.db')
    c = conn.cursor()
    c.execute("UPDATE users SET balance=? WHERE id=?", (new_bal, user_id))
    conn.commit()
    conn.close()

# --- UTILS ---
def get_card():
    cards = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    return random.choice(cards)

def card_value(card):
    if card in ['10', 'J', 'Q', 'K']: return 0
    if card == 'A': return 1
    return int(card)

def calculate_score(hand):
    return sum(card_value(c) for c in hand) % 10

# --- GIAO DIỆN CHÍNH ---
@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    balance = get_balance(message.from_user.id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🎲 Tài Xỉu", callback_data="menu_tx"),
        types.InlineKeyboardButton("🃏 Baccarat", callback_data="menu_bc"),
        types.InlineKeyboardButton("🦀 Bầu Cua", callback_data="menu_bcua"),
        types.InlineKeyboardButton("🐓 Đá Gà", callback_data="menu_daga")
    )
    bot.send_message(message.chat.id, f"🎮 **CASINO TELEGRAM** 🎮\n\n👤 ID: `{message.from_user.id}`\n💰 Ví: `{balance:,} VNĐ`", parse_mode="Markdown", reply_markup=markup)

# --- 1. XỬ LÝ TÀI XỈU ---
@bot.callback_query_handler(func=lambda call: call.data == "menu_tx")
def tx_menu(call):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Tài (11-17)", callback_data="play_tx_tai"),
               types.InlineKeyboardButton("Xỉu (4-10)", callback_data="play_tx_xiu"))
    bot.edit_message_text("🎲 **TÀI XỈU**\nCược: 5,000đ. Chọn cửa:", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("play_tx_"))
def play_tx(call):
    user_id = call.from_user.id
    if get_balance(user_id) < 5000: return bot.answer_callback_query(call.id, "Không đủ tiền!")
    
    bet = call.data.split("_")[2]
    dice = [random.randint(1, 6) for _ in range(3)]
    total = sum(dice)
    res = "tai" if total >= 11 else "xiu"
    
    change = 5000 if bet == res else -5000
    update_balance(user_id, change)
    
    txt = "🎉 THẮNG" if change > 0 else "💀 THUA"
    bot.edit_message_text(f"🎲 Kết quả: {dice[0]}-{dice[1]}-{dice[2]} = **{total}** ({res.upper()})\n{txt}!\n💰 Ví: {get_balance(user_id):,}đ", 
                          call.message.chat.id, call.message.message_id, parse_mode="Markdown",
                          reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Chơi tiếp", callback_data="menu_tx")))

# --- 2. XỬ LÝ BACCARAT ---
@bot.callback_query_handler(func=lambda call: call.data == "menu_bc")
def bc_menu(call):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Player (x2)", callback_data="play_bc_player"),
               types.InlineKeyboardButton("Banker (x1.95)", callback_data="play_bc_banker"))
    bot.edit_message_text("🃏 **BACCARAT**\nCược: 5,000đ. Chọn cửa:", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("play_bc_"))
def play_bc(call):
    user_id = call.from_user.id
    if get_balance(user_id) < 5000: return bot.answer_callback_query(call.id, "Không đủ tiền!")
    
    bet = call.data.split("_")[2]
    p_h, b_h = [get_card(), get_card()], [get_card(), get_card()]
    p_s, b_s = calculate_score(p_h), calculate_score(b_h)
    
    # Luật đơn giản: rút lá 3 nếu < 6
    if p_s < 6: p_h.append(get_card()); p_s = calculate_score(p_h)
    if b_s < 6: b_h.append(get_card()); b_s = calculate_score(b_h)
    
    win = "tie"
    if p_s > b_s: win = "player"
    elif b_s > p_s: win = "banker"
    
    change = 5000 if bet == win else -5000
    update_balance(user_id, change)
    
    bot.edit_message_text(f"🃏 Player: {' '.join(p_h)} ({p_s})\n🃏 Banker: {' '.join(b_h)} ({b_s})\n{'🎉 THẮNG' if change>0 else '💀 THUA'}\nVí: {get_balance(user_id):,}đ",
                          call.message.chat.id, call.message.message_id,
                          reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Lại", callback_data="menu_bc")))

# --- 3. XỬ LÝ BẦU CUA ---
@bot.callback_query_handler(func=lambda call: call.data == "menu_bcua")
def bcua_menu(call):
    items = [("🦀 Cua", "cua"), ("🦐 Tôm", "tom"), ("🐟 Cá", "ca"), ("🐔 Gà", "ga"), ("🦌 Nai", "nai"), ("🎃 Bầu", "bau")]
    markup = types.InlineKeyboardMarkup(row_width=3)
    btns = [types.InlineKeyboardButton(i[0], callback_data=f"play_bcua_{i[1]}") for i in items]
    markup.add(*btns)
    bot.edit_message_text("🦀 **BẦU CUA**\nCược 5,000đ. Chọn linh vật:", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("play_bcua_"))
def play_bcua(call):
    user_id = call.from_user.id
    if get_balance(user_id) < 5000: return bot.answer_callback_query(call.id, "Không đủ tiền!")
    
    bet = call.data.split("_")[2]
    icons = {"bau": "🎃", "cua": "🦀", "tom": "🦐", "ca": "🐟", "ga": "🐔", "nai": "🦌"}
    res_keys = random.choices(list(icons.keys()), k=3)
    res_icons = [icons[k] for k in res_keys]
    
    win_count = res_keys.count(bet)
    change = (win_count * 5000) if win_count > 0 else -5000
    update_balance(user_id, change)
    
    txt = f"🎉 THẮNG x{win_count}" if win_count > 0 else "💀 THUA"
    bot.edit_message_text(f"🎲 Kết quả: {' '.join(res_icons)}\n{txt}!\nVí: {get_balance(user_id):,}đ",
                          call.message.chat.id, call.message.message_id,
                          reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Lại", callback_data="menu_bcua")))

# --- 4. XỬ LÝ ĐÁ GÀ ---
@bot.callback_query_handler(func=lambda call: call.data == "menu_daga")
def daga_menu(call):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔴 Gà Meron", callback_data="play_daga_meron"),
               types.InlineKeyboardButton("🔵 Gà Wala", callback_data="play_daga_wala"))
    bot.edit_message_text("🐓 **ĐÁ GÀ SV388**\nCược 5,000đ. Chọn chiến kê:", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("play_daga_"))
def play_daga(call):
    user_id = call.from_user.id
    if get_balance(user_id) < 5000: return bot.answer_callback_query(call.id, "Không đủ tiền!")
    
    bet = call.data.split("_")[2]
    bot.edit_message_text("🐓 Trận đấu đang diễn ra... ⚔️", call.message.chat.id, call.message.message_id)
    time.sleep(2)
    
    win = random.choice(["meron", "wala"])
    change = 5000 if bet == win else -5000
    update_balance(user_id, change)
    
    res_name = "🔴 MERON" if win == "meron" else "🔵 WALA"
    bot.edit_message_text(f"🏁 Kết quả: **{res_name}** thắng!\n{'🎉 Bạn chọn đúng!' if change>0 else '💀 Gà của bạn đã gục...'}\nVí: {get_balance(user_id):,}đ",
                          call.message.chat.id, call.message.message_id, parse_mode="Markdown",
                          reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Trận mới", callback_data="menu_daga")))

if __name__ == "__main__":
    init_db()
    print("Bot đang chạy...")
    bot.infinity_polling()
