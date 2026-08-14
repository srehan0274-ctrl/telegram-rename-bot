import os
from flask import Flask, request
import telebot

TOKEN = os.environ["BOT_TOKEN"]

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

user_files = {}

@bot.message_handler(commands=["start"])
def start(message):
    print("🔥 START HANDLER CALLED")

    bot.reply_to(
        message,
        "👋 Welcome!\n\n"
        "Mujhe koi document/file bhejo.\n"
        "Uske baad naya filename bhejna."
    )
@bot.message_handler(content_types=["document"])
def receive_file(message):
    file = message.document

    user_files[message.from_user.id] = {
        "file_id": file.file_id,
        "old_name": file.file_name
    }

    bot.reply_to(
        message,
        f"📁 File received:\n{file.file_name}\n\n"
        "Ab naya filename bhejo.\n"
        "Example: movie.mp4"
    )


@bot.message_handler(
    func=lambda message: message.from_user.id in user_files,
    content_types=["text"]
)
def rename_file(message):
    user_id = message.from_user.id
    new_name = os.path.basename(message.text.strip())

    if not new_name:
        bot.reply_to(message, "❌ Invalid filename.")
        return

    file_info = user_files[user_id]
    temp_file = f"/tmp/{user_id}_{new_name}"

    try:
        bot.send_message(message.chat.id, "⏳ Processing...")

        file_data = bot.get_file(file_info["file_id"])
        downloaded_file = bot.download_file(file_data.file_path)

        with open(temp_file, "wb") as f:
            f.write(downloaded_file)

        with open(temp_file, "rb") as f:
            bot.send_document(
                message.chat.id,
                f,
                caption=f"✅ Renamed successfully!\n📄 {new_name}"
            )

        os.remove(temp_file)
        del user_files[user_id]

    except Exception as e:
        if os.path.exists(temp_file):
            os.remove(temp_file)

        bot.reply_to(message, f"❌ Error: {e}")

@app.route("/webhook", methods=["POST"])
def webhook():
    print("🔥🔥 WEBHOOK HIT 🔥🔥", flush=True)

    try:
        data = request.get_data().decode("utf-8")
        print("TELEGRAM DATA:", data, flush=True)

        update = telebot.types.Update.de_json(data)

        print("PROCESSING UPDATE...", flush=True)
        bot.process_new_updates([update])

        print("UPDATE DONE", flush=True)
        return "OK", 200

    except Exception as e:
        print("❌ WEBHOOK ERROR:", repr(e), flush=True)
        return "ERROR", 500
        
def setup_webhook():
    render_url = os.environ.get("RENDER_EXTERNAL_URL")

    if not render_url:
        print("ERROR: RENDER_EXTERNAL_URL missing")
        return

    webhook_url = render_url.rstrip("/") + "/webhook"

    print("Setting webhook:", webhook_url)

    try:
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)
        print("WEBHOOK SET SUCCESSFULLY")
    except Exception as e:
        print("WEBHOOK ERROR:", e)


setup_webhook()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
