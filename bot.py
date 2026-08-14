import os
import threading
from flask import Flask, request
import telebot

TOKEN = os.environ["8654669792:AAHnypyuxuiu8JQ5HI8RL8tix7VizBqn5JQ"]

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

user_files = {}


@bot.message_handler(commands=["start"])
def start(message):
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
    func=lambda message: message.from_user.id in user_files
)
def rename_file(message):
    user_id = message.from_user.id
    new_name = message.text.strip()

    if not new_name:
        bot.reply_to(message, "❌ Filename empty nahi ho sakta.")
        return

    # Safe filename
    new_name = os.path.basename(new_name)

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


@app.route("/", methods=["GET"])
def home():
    return "Rename Bot is running!"


@app.route("/webhook", methods=["POST"])
def webhook():
    json_string = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "OK", 200


def setup_webhook():
    render_url = os.environ.get("RENDER_EXTERNAL_URL")

    if render_url:
        webhook_url = render_url + "/webhook"
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)


if __name__ == "__main__":
    setup_webhook()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
