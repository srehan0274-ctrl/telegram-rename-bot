import os
from flask import Flask, request
import telebot
from telebot import types

TOKEN = os.environ["BOT_TOKEN"]

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# User ka temporary data
user_data = {}


# =========================
# START
# =========================

@bot.message_handler(commands=["start"])
def start(message):
    user_data.pop(message.from_user.id, None)

    bot.reply_to(
        message,
        "👋 Welcome!\n\n"
        "🎬 Mujhe normal video bhejo.\n"
        "Uske baad naya filename bhejo.\n"
        "Phir thumbnail photo bhejo.\n\n"
        "Example filename:\n"
        "movie.mp4"
    )


# =========================
# VIDEO RECEIVE
# =========================

@bot.message_handler(content_types=["video"])
def receive_video(message):

    user_id = message.from_user.id

    video = message.video

    user_data[user_id] = {
        "video_id": video.file_id,
        "old_name": video.file_name or "video.mp4",
        "new_name": None,
        "thumbnail_id": None
    }

    bot.reply_to(
        message,
        f"🎬 Video received!\n\n"
        f"📄 Old name: {video.file_name or 'video.mp4'}\n\n"
        "✏️ Ab naya filename bhejo.\n\n"
        "Example:\n"
        "movie.mp4"
    )


# =========================
# FILENAME RECEIVE
# =========================

@bot.message_handler(
    func=lambda message:
    message.from_user.id in user_data
    and user_data[message.from_user.id]["new_name"] is None
    and bool(message.text)
)
def receive_filename(message):

    user_id = message.from_user.id

    new_name = message.text.strip()

    # Safe filename
    new_name = os.path.basename(new_name)

    if not new_name:
        bot.reply_to(message, "❌ Invalid filename.")
        return

    # Agar extension nahi di
    if "." not in new_name:
        new_name += ".mp4"

    user_data[user_id]["new_name"] = new_name

    bot.reply_to(
        message,
        f"✅ Filename set:\n"
        f"{new_name}\n\n"
        "🖼️ Ab thumbnail photo bhejo.\n\n"
        "Thumbnail nahi chahiye to:\n"
        "/skip"
    )


# =========================
# SKIP THUMBNAIL
# =========================

@bot.message_handler(commands=["skip"])
def skip_thumbnail(message):

    user_id = message.from_user.id

    if user_id not in user_data:
        bot.reply_to(
            message,
            "❌ Pehle video bhejo."
        )
        return

    if not user_data[user_id]["new_name"]:
        bot.reply_to(
            message,
            "❌ Pehle filename bhejo."
        )
        return

    process_video(message, None)


# =========================
# THUMBNAIL RECEIVE
# =========================

@bot.message_handler(content_types=["photo"])
def receive_thumbnail(message):

    user_id = message.from_user.id

    if user_id not in user_data:
        bot.reply_to(
            message,
            "❌ Pehle video bhejo."
        )
        return

    if not user_data[user_id]["new_name"]:
        bot.reply_to(
            message,
            "❌ Pehle filename bhejo."
        )
        return

    # Sabse high quality photo
    thumbnail = message.photo[-1]

    user_data[user_id]["thumbnail_id"] = thumbnail.file_id

    bot.reply_to(
        message,
        "🖼️ Thumbnail received!\n"
        "⏳ Processing..."
    )

    process_video(message, thumbnail.file_id)


# =========================
# PROCESS VIDEO
# =========================

def process_video(message, thumbnail_id):

    user_id = message.from_user.id

    if user_id not in user_data:
        return

    data = user_data[user_id]

    video_path = f"/tmp/{user_id}_video.mp4"
    thumb_path = f"/tmp/{user_id}_thumb.jpg"

    try:

        # -------------------------
        # DOWNLOAD VIDEO
        # -------------------------

        bot.send_message(
            message.chat.id,
            "📥 Video download ho raha hai..."
        )

        file_info = bot.get_file(data["video_id"])

        downloaded_video = bot.download_file(
            file_info.file_path
        )

        with open(video_path, "wb") as f:
            f.write(downloaded_video)

        # -------------------------
        # DOWNLOAD THUMBNAIL
        # -------------------------

        thumbnail_file = None

        if thumbnail_id:

            thumb_info = bot.get_file(thumbnail_id)

            downloaded_thumb = bot.download_file(
                thumb_info.file_path
            )

            with open(thumb_path, "wb") as f:
                f.write(downloaded_thumb)

            thumbnail_file = open(
                thumb_path,
                "rb"
            )

        # -------------------------
        # SEND NORMAL VIDEO
        # -------------------------

        bot.send_message(
            message.chat.id,
            "📤 Video upload ho raha hai..."
        )

        video_file = types.InputFile(
            video_path
        )

        bot.send_video(
            message.chat.id,
            video_file,
            caption=(
                f"✅ Video ready!\n\n"
                f"📄 {data['new_name']}"
            ),
            thumbnail=thumbnail_file,
            supports_streaming=True
        )

        # Close thumbnail
        if thumbnail_file:
            thumbnail_file.close()

        # -------------------------
        # CLEAN FILES
        # -------------------------

        if os.path.exists(video_path):
            os.remove(video_path)

        if os.path.exists(thumb_path):
            os.remove(thumb_path)

        # User data delete
        del user_data[user_id]

    except Exception as e:

        # Close/delete files
        try:
            if os.path.exists(video_path):
                os.remove(video_path)

            if os.path.exists(thumb_path):
                os.remove(thumb_path)
        except:
            pass

        bot.reply_to(
            message,
            f"❌ Error:\n{e}"
        )


# =========================
# HOME
# =========================

@app.route("/", methods=["GET"])
def home():
    return "Rename + Thumbnail Bot is running!"


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

        webhook_url = (
            render_url.rstrip("/")
            + "/webhook"
        )

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
