import os
from flask import Flask, request
import telebot

TOKEN = os.environ["BOT_TOKEN"]

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

user_files = {}
user_thumbnails = {}


# =========================
# START
# =========================

@bot.message_handler(commands=["start"])
def start(message):
    print("🔥 START HANDLER CALLED")

    bot.reply_to(
        message,
        "👋 Welcome!\n\n"
        "Mujhe koi video/file bhejo.\n"
        "Uske baad naya filename bhejna.\n"
        "Phir thumbnail photo bhejna.\n\n"
        "Example:\n"
        "movie.mp4"
    )


# =========================
# RECEIVE FILE
# =========================

@bot.message_handler(content_types=["document"])
def receive_file(message):
    file = message.document

    user_files[message.from_user.id] = {
        "file_id": file.file_id,
        "old_name": file.file_name
    }

    bot.reply_to(
        message,
        f"📁 File received!\n\n"
        f"Old name: {file.file_name}\n\n"
        f"Ab naya filename bhejo.\n"
        f"Example: movie.mp4"
    )


# =========================
# RECEIVE NEW FILENAME
# =========================

@bot.message_handler(
    func=lambda message:
    message.from_user.id in user_files
    and message.content_type == "text"
    and not message.text.startswith("/")
)
def receive_filename(message):

    user_id = message.from_user.id
    new_name = message.text.strip()

    new_name = os.path.basename(new_name)

    if not new_name:
        bot.reply_to(message, "❌ Invalid filename.")
        return

    user_files[user_id]["new_name"] = new_name

    bot.reply_to(
        message,
        f"✅ New filename set:\n{new_name}\n\n"
        f"🖼️ Ab thumbnail photo bhejo.\n"
        f"Thumbnail nahi chahiye to /skip bhejo."
    )


# =========================
# RECEIVE THUMBNAIL
# =========================

@bot.message_handler(content_types=["photo"])
def receive_thumbnail(message):

    user_id = message.from_user.id

    if user_id not in user_files:
        bot.reply_to(
            message,
            "❌ Pehle mujhe file/video bhejo."
        )
        return

    if "new_name" not in user_files[user_id]:
        bot.reply_to(
            message,
            "❌ Pehle new filename bhejo."
        )
        return

    # Highest quality photo
    photo = message.photo[-1]

    user_thumbnails[user_id] = photo.file_id

    bot.reply_to(
        message,
        "🖼️ Thumbnail received!\n\n"
        "⏳ Processing..."
    )

    process_file(message.chat.id, user_id)


# =========================
# SKIP THUMBNAIL
# =========================

@bot.message_handler(commands=["skip"])
def skip_thumbnail(message):

    user_id = message.from_user.id

    if user_id not in user_files:
        bot.reply_to(
            message,
            "❌ Pehle file/video bhejo."
        )
        return

    if "new_name" not in user_files[user_id]:
        bot.reply_to(
            message,
            "❌ Pehle new filename bhejo."
        )
        return

    bot.reply_to(
        message,
        "⏳ Processing without thumbnail..."
    )

    process_file(message.chat.id, user_id)


# =========================
# PROCESS FILE
# =========================

def process_file(chat_id, user_id):

    file_info = user_files[user_id]

    new_name = file_info["new_name"]
    file_id = file_info["file_id"]

    temp_file = f"/tmp/{user_id}_{new_name}"

    try:

        # Download original file
        file_data = bot.get_file(file_id)

        downloaded_file = bot.download_file(
            file_data.file_path
        )

        with open(temp_file, "wb") as f:
            f.write(downloaded_file)

        # Thumbnail available?
        thumbnail_file = None

        if user_id in user_thumbnails:

            thumb_id = user_thumbnails[user_id]

            thumb_data = bot.get_file(thumb_id)

            thumb_bytes = bot.download_file(
                thumb_data.file_path
            )

            thumbnail_file = f"/tmp/{user_id}_thumb.jpg"

            with open(thumbnail_file, "wb") as f:
                f.write(thumb_bytes)

        # Send renamed file
        with open(temp_file, "rb") as f:

            if thumbnail_file:

                with open(thumbnail_file, "rb") as thumb:

                    bot.send_document(
                        chat_id,
                        f,
                        visible_file_name=new_name,
                        thumbnail=thumb,
                        caption=(
                            f"✅ Renamed successfully!\n\n"
                            f"📄 {new_name}\n"
                            f"🖼️ Custom thumbnail added"
                        )
                    )

            else:

                bot.send_document(
                    chat_id,
                    f,
                    visible_file_name=new_name,
                    caption=(
                        f"✅ Renamed successfully!\n\n"
                        f"📄 {new_name}"
                    )
                )

        # Delete temporary files
        if os.path.exists(temp_file):
            os.remove(temp_file)

        if thumbnail_file and os.path.exists(thumbnail_file):
            os.remove(thumbnail_file)

        # Clear user data
        del user_files[user_id]

        if user_id in user_thumbnails:
            del user_thumbnails[user_id]

        print("✅ FILE PROCESSING COMPLETE")

    except Exception as e:

        print("❌ ERROR:", e)

        if os.path.exists(temp_file):
            os.remove(temp_file)

        bot.send_message(
            chat_id,
            f"❌ Error:\n{e}"
        )


# =========================
# HOME
# =========================

@app.route("/", methods=["GET"])
def home():
    return "Rename Bot is running!"


# =========================
# WEBHOOK
# =========================

@app.route("/webhook", methods=["POST"])
def webhook():

    json_string = request.get_data().decode("utf-8")

    update = telebot.types.Update.de_json(
        json_string
    )

    bot.process_new_updates([update])

    return "OK", 200


# =========================
# SET WEBHOOK
# =========================

def setup_webhook():

    render_url = os.environ.get(
        "RENDER_EXTERNAL_URL"
    )

    if render_url:

        webhook_url = render_url + "/webhook"

        bot.remove_webhook()

        bot.set_webhook(
            url=webhook_url
        )

        print(
            "WEBHOOK SET SUCCESSFULLY:",
            webhook_url
        )


setup_webhook()


# =========================
# RUN
# =========================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
        )
