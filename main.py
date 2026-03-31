from os import getenv
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

# Holatlar (States) - ADD_TITLE olib tashlandi
ADMIN_PASSWORD, ADMIN_MENU, ADD_CONTENT, VIEW_ENTRIES, DELETE_CONFIRM = range(5)

db = Database()
ai = AIHandler()

ADMIN_PASS = getenv("ADMIN_PASSWORD")

# ─── USER: savol-javob ───────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Assalomu alaykum! Men Advokat Botman.\n"
        "Savolingizni yozing, men bazadagi ma'lumotlar asosida javob beraman.\n\n"
        "📌 Admin kirishi: /admin"
    )

async def handle_user_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("is_admin"):
        return
    
    question = update.message.text
    await update.message.reply_text("🔍 Savolingiz tahlil qilinmoqda...")
    
    entries = db.get_all_entries()
    if not entries:
        await update.message.reply_text("⚠️ Hozircha baza bo'sh.")
        return
    
    answer = await ai.get_answer(question, entries)
    await update.message.reply_text(answer, parse_mode="HTML")

# ─── ADMIN: login ────────────────────────────────────────────────────────────

async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("🔐 Admin parolini kiriting:")
    return ADMIN_PASSWORD

async def admin_check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == ADMIN_PASS:
        context.user_data["is_admin"] = True
        await update.message.reply_text("✅ Tizimga kirildi.")
        await show_admin_menu(update, context)
        return ADMIN_MENU
    else:
        await update.message.reply_text("❌ Parol xato. Qayta urinib ko'ring:")
        return ADMIN_PASSWORD

# ─── ADMIN: menyular ─────────────────────────────────────────────────────────

async def show_admin_menu(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    count = db.get_count()
    keyboard = [
        [InlineKeyboardButton("➕ Matn qo'shish", callback_data="add")],
        [InlineKeyboardButton(f"📋 Ma'lumotlar ({count})", callback_data="list")],
        [InlineKeyboardButton("🚪 Chiqish", callback_data="logout")],
    ]
    markup = InlineKeyboardMarkup(keyboard)
    text = f"🛠 *Admin Panel*\nBazada {count} ta ma'lumot bor."
    
    if hasattr(update_or_query, 'message') and update_or_query.message:
        await update_or_query.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")
    else:
        await update_or_query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "add":
        await query.edit_message_text("📝 Bazaga qo'shiladigan matnni yuboring:")
        return ADD_CONTENT

    elif data == "list":
        entries = db.get_all_entries()
        if not entries:
            keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data="menu")]]
            await query.edit_message_text("📭 Baza bo'sh.", reply_markup=InlineKeyboardMarkup(keyboard))
            return ADMIN_MENU
        
        keyboard = []
        for entry in entries:
            # Sarlavha yo'qligi uchun matnning boshini ko'rsatamiz
            display_text = entry['content'][:30].replace('\n', ' ') + "..."
            keyboard.append([InlineKeyboardButton(f"📄 {display_text}", callback_data=f"view_{entry['id']}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="menu")])
        await query.edit_message_text("📋 *Mavjud ma'lumotlar:*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return VIEW_ENTRIES

    elif data == "menu":
        await show_admin_menu(query, context)
        return ADMIN_MENU

    elif data == "logout":
        context.user_data.clear()
        await query.edit_message_text("👋 Chiqildi.")
        return ConversationHandler.END

    elif data.startswith("view_"):
        entry_id = int(data.split("_")[1])
        entry = db.get_entry(entry_id)
        if entry:
            keyboard = [
                [InlineKeyboardButton("🗑 O'chirish", callback_data=f"delete_{entry_id}")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="list")],
            ]
            await query.edit_message_text(f"📄 *Ma'lumot:*\n\n{entry['content']}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return VIEW_ENTRIES

    elif data.startswith("delete_"):
        entry_id = int(data.split("_")[1])
        keyboard = [[InlineKeyboardButton("✅ O'chirish", callback_data=f"confirm_{entry_id}"), InlineKeyboardButton("❌ Yo'q", callback_data="list")]]
        await query.edit_message_text("⚠️ Ushbu matnni o'chirmoqchimisiz?", reply_markup=InlineKeyboardMarkup(keyboard))
        return DELETE_CONFIRM

    elif data.startswith("confirm_"):
        entry_id = int(data.split("_")[1])
        db.delete_entry(entry_id)
        await query.answer("✅ O'chirildi!")
        await show_admin_menu(query, context)
        return ADMIN_MENU

    return ADMIN_MENU

# ─── ADMIN: matnni saqlash ──────────────────────────────────────────────────

async def add_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    content = update.message.text
    # Sarlavha sifatida matnning birinchi 30 ta belgisini avtomatik olamiz (DB xatosi bermasligi uchun)
    title = content[:30] + "..." if len(content) > 30 else content
    db.add_entry(title, content)
    await update.message.reply_text("✅ Matn muvaffaqiyatli saqlandi!")
    await show_admin_menu(update, context)
    return ADMIN_MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Bekor qilindi.")
    return ConversationHandler.END

# ─── MAIN ────────────────────────────────────────────────────────────────────

async def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN topilmadi!")
    
    db.init()
    app = Application.builder().token(token).build()
    
    admin_conv = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_start)],
        states={
            ADMIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_check_password)],
            ADMIN_MENU: [CallbackQueryHandler(admin_callback)],
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
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    
    stop_event = asyncio.Event()
    await stop_event.wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtadi.")
