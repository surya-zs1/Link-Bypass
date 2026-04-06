import os
from flask import Flask
from threading import Thread
from FZBypass import Bypass, LOGGER, Config
from pyrogram import idle
from pyrogram.filters import command, user
from os import path as ospath, execl
from asyncio import create_subprocess_exec
from sys import executable

# --- Render Port Binding Start ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "FZBypassBot is running!"

def run_server():
    # Render automatically provides the PORT environment variable
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
# --- Render Port Binding End ---

@Bypass.on_message(command("restart") & user(Config.OWNER_ID))
async def restart_cmd(client, message):
    restart_message = await message.reply("<i>Restarting...</i>")
    await (await create_subprocess_exec("python3", "update.py")).wait()
    with open(".restartmsg", "w") as f:
        f.write(f"{restart_message.chat.id}\n{restart_message.id}\n")
    try:
        execl(executable, executable, "-m", "FZBypass")
    except Exception:
        execl(executable, executable, "-m", "FZBypassBot/FZBypass")

async def restart_status():
    if ospath.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            try:
                lines = f.readlines()
                if len(lines) >= 2:
                    chat_id = int(lines[0].strip())
                    msg_id = int(lines[1].strip())
                    await Bypass.edit_message_text(
                        chat_id=chat_id, message_id=msg_id, text="<i>Restarted !</i>"
                    )
            except Exception as e:
                LOGGER.error(f"Restart status error: {e}")
        if ospath.exists(".restartmsg"):
            os.remove(".restartmsg")

# Start the web server in a separate thread before starting the bot
Thread(target=run_server, daemon=True).start()
LOGGER.info("Web server started for Render port binding.")

Bypass.start()
LOGGER.info("FZ Bot Started!")
Bypass.loop.run_until_complete(restart_status())
idle()
Bypass.stop()
