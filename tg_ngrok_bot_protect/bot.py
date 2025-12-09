import logging
import threading
import time
from pyngrok import ngrok
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

PASSWORD = "cw74"

user_states = {}
active_tunnels = {}
server_threads = {}

logging.basicConfig(level=logging.INFO)

def start_local_server(port):
    import http.server
    import socketserver
    import os
    os.chdir("site")
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("0.0.0.0", port), handler) as httpd:
        httpd.serve_forever()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите пароль:")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.effective_chat.id

    # Password auth
    if chat_id not in user_states:
        if text == PASSWORD:
            user_states[chat_id] = "AUTH"
            keyboard = [["Запустить сайт"], ["Закрыть сайт"]]
            await update.message.reply_text("Авторизация успешна.", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        else:
            await update.message.reply_text("❌ Неверный пароль.")
        return

    # Prevent double launch
    if text == "Запустить сайт":
        if chat_id in active_tunnels:
            await update.message.reply_text("⚠ Сайт уже запущен!")
            return
        user_states[chat_id] = "ASK_TOKEN"
        await update.message.reply_text("Введите NGROK токен:")
        return

    state = user_states.get(chat_id)

    if state == "ASK_TOKEN":
        context.user_data["token"] = text.strip()
        user_states[chat_id] = "ASK_PORT"
        await update.message.reply_text("Введите порт (например 8080):")
        return

    if state == "ASK_PORT":
        try:
            port = int(text)
        except:
            await update.message.reply_text("❌ Неверный порт.")
            return

        token = context.user_data["token"]

        try:
            ngrok.set_auth_token(token)
        except Exception:
            await update.message.reply_text("❌ Неверный токен NGROK.")
            return

        # Start server thread
        th = threading.Thread(target=start_local_server, args=(port,), daemon=True)
        server_threads[chat_id] = th
        th.start()

        time.sleep(1)
        tunnel = ngrok.connect(port, "http")
        active_tunnels[chat_id] = tunnel

        await update.message.reply_text(f"✅ Сайт запущен!
Ссылка: {tunnel.public_url}")
        user_states[chat_id] = "AUTH"
        return

    if text == "Закрыть сайт":
        if chat_id in active_tunnels:
            ngrok.disconnect(active_tunnels[chat_id].public_url)
            del active_tunnels[chat_id]
            await update.message.reply_text("🛑 Сайт остановлен.")
        else:
            await update.message.reply_text("Сайт не запущен.")
        return

async def main():
    app = ApplicationBuilder().token("8370248542:AAFb9DPrV82mFQC6sQ1TLm9c3H35tfLbq3g").build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
