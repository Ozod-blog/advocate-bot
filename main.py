import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, ConversationHandler, filters
)
from database import Database
from ai_handler import AIHandler
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# States
ADMIN_PASSWORD, ADMIN_MENU, ADD_TITLE, ADD_CONTENT, VIEW_ENTRIES, DELETE_CONFIRM = range(6)

db = Database()
ai = AIHandler()

ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "admin123")


# ─── USER: savol-javob ───────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Assalomu alaykum! Men Advokat Botman.\n\n"
        "Huquqiy savolingizni yozing — men bazamizdagi ma'lumotlar asosida javob beraman.\n\n"
        "📌 Admin: /admin"
    )

async def handle_user_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Admin sessiyasida bo'lsa, adminga yo'naltirish
    if context.user_data.get("is_admin"):
        return
    
    question = update.message.text
    await update.message.reply_text("🔍 Savolingiz tahlil qilinmoqda...")
    
    entries = db.get_all_entries()
    if not entries:
        await update.message.reply_text(
            "⚠️ Hozircha baza bo'sh. Tez orada ma'lumotlar qo'shiladi."
        )
        return
    
    answer = await ai.get_answer(question, entries)
    await update.message.reply_text(answer, parse_mode="Markdown")


# ─── ADMIN: login ────────────────────────────────────────────────────────────

async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("🔐 Admin panelga kirish uchun parolni yuboring:")
    return ADMIN_PASSWORD

async def admin_check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == ADMIN_PASS:
        context.user_data["is_admin"] = True
        await update.message.reply_text("✅ Xush kelibsiz, Admin!")
        await show_admin_menu(update, context)
        return ADMIN_MENU
    else:
        await update.message.reply_text("❌ Parol noto'g'ri. Qaytadan urinib ko'ring:")
        return ADMIN_PASSWORD


# ─── ADMIN: menyular ─────────────────────────────────────────────────────────

async def show_admin_menu(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    count = db.get_count()
    keyboard = [
        [InlineKeyboardButton("➕ Ma'lumot qo'shish", callback_data="add")],
        [InlineKeyboardButton(f"📋 Barcha ma'lumotlar ({count})", callback_data="list")],
        [InlineKeyboardButton("🚪 Chiqish", callback_data="logout")],
    ]
    markup = InlineKeyboardMarkup(keyboard)
    text = f"🛠 *Admin Panel*\nBazada {count} ta ma'lumot mavjud."
    
    if hasattr(update_or_query, 'message'):
        await update_or_query.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")
    else:
        await update_or_query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "add":
        await query.edit_message_text("📝 Sarlavhani yozing (qisqa nom):")
        return ADD_TITLE

    elif data == "list":
        entries = db.get_all_entries()
        if not entries:
            keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data="menu")]]
            await query.edit_message_text(
                "📭 Baza bo'sh.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ADMIN_MENU
        
        keyboard = []
        for entry in entries:
            keyboard.append([
                InlineKeyboardButton(
                    f"📄 {entry['title'][:35]}",
                    callback_data=f"view_{entry['id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="menu")])
        await query.edit_message_text(
            "📋 *Barcha ma'lumotlar:*\nKo'rish yoki o'chirish uchun bosing.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return VIEW_ENTRIES

    elif data == "menu":
        await show_admin_menu(query, context)
        return ADMIN_MENU

    elif data == "logout":
        context.user_data.clear()
        await query.edit_message_text("👋 Admin paneldan chiqdingiz.")
        return ConversationHandler.END

    elif data.startswith("view_"):
        entry_id = int(data.split("_")[1])
        entry = db.get_entry(entry_id)
        if entry:
            # Content ni 3000 belgidan oshmasin
            content_preview = entry['content'][:3000]
            if len(entry['content']) > 3000:
                content_preview += "..."
            
            keyboard = [
                [InlineKeyboardButton("🗑 O'chirish", callback_data=f"delete_{entry_id}")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="list")],
            ]
            await query.edit_message_text(
                f"📄 *{entry['title']}*\n\n{content_preview}",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        return VIEW_ENTRIES

    elif data.startswith("delete_"):
        entry_id = int(data.split("_")[1])
        context.user_data["delete_id"] = entry_id
        entry = db.get_entry(entry_id)
        keyboard = [
            [
                InlineKeyboardButton("✅ Ha, o'chir", callback_data=f"confirm_delete_{entry_id}"),
                InlineKeyboardButton("❌ Yo'q", callback_data="list"),
            ]
        ]
        await query.edit_message_text(
            f"⚠️ *{entry['title']}* ni o'chirishni tasdiqlaysizmi?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return DELETE_CONFIRM

    elif data.startswith("confirm_delete_"):
        entry_id = int(data.split("_")[2])
        db.delete_entry(entry_id)
        await query.answer("✅ O'chirildi!")
        await show_admin_menu(query, context)
        return ADMIN_MENU

    return ADMIN_MENU


# ─── ADMIN: ma'lumot qo'shish ────────────────────────────────────────────────

async def add_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_title"] = update.message.text
    await update.message.reply_text(
        f"✅ Sarlavha: *{update.message.text}*\n\nEndi to'liq matnni yuboring:",
        parse_mode="Markdown"
    )
    return ADD_CONTENT

async def add_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = context.user_data.get("new_title")
    content = update.message.text
    db.add_entry(title, content)
    await update.message.reply_text(f"✅ *{title}* bazaga qo'shildi!", parse_mode="Markdown")
    await show_admin_menu(update, context)
    return ADMIN_MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Bekor qilindi.")
    return ConversationHandler.END


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN .env faylida yo'q!")
    
    db.init()
    
    app = Application.builder().token(token).build()
    
    # Admin conversation
    admin_conv = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_start)],
        states={
            ADMIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_check_password)],
            ADMIN_MENU: [CallbackQueryHandler(admin_callback)],
            ADD_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_title),
                CallbackQueryHandler(admin_callback),
            ],
            ADD_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_content)],
            VIEW_ENTRIES: [CallbackQueryHandler(admin_callback)],
            DELETE_CONFIRM: [CallbackQueryHandler(admin_callback)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(admin_conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_question))
    
    logger.info("Bot ishga tushdi...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtadi.")
