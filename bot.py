import os
import telebot

TOKEN = os.getenv("8654669792:AAHnypyuxuiu8JQ5HI8RL8tix7VizBqn5JQ")

bot = telebot.TeleBot(TOKEN)

user_files = {}


@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(
        message,
        "👋 Welcome!\n\n"
        "Mujhe koi file/document bhejo.\n"
        "Main tumse naya filename puchunga."
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


@bot.message_handler(func=lambda message: message.from_user.id in user_files)
def rename_file(message):
    user_id = message.from_user.id
    new_name = message.text.strip()

    if not new_name:
        bot.reply_to(message, "❌ Filename empty nahi ho sakta.")
        return

    file_info = user_files[user_id]

    try:
        msg = bot.reply_to(message, "⏳ File download ho rahi hai...")

        file_data = bot.get_file(file_info["file_id"])
        downloaded_file = bot.download_file(file_data.file_path)

        with open(new_name, "wb") as f:
            f.write(downloaded_file)

        bot.edit_message_text(
            "📤 File upload ho rahi hai...",
            message.chat.id,
            msg.message_id
        )

        with open(new_name, "rb") as f:
            bot.send_document(
                message.chat.id,
                f,
                caption=f"✅ Renamed successfully!\n\n📄 {new_name}"
            )

        os.remove(new_name)
        del user_files[user_id]

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")


print("🤖 Rename Bot is running...")

bot.infinity_polling()
