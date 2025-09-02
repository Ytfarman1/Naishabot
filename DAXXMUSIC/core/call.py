import asyncio
import os
import random
import glob
import json
from datetime import datetime, timedelta
from typing import Union

import yt_dlp
from pytgcalls import PyTgCalls, idle
from pytgcalls.types.input_stream import InputStream, AudioPiped
from pytgcalls.exceptions import NoActiveGroupCall

from DAXXMUSIC import app
from DAXXMUSIC.misc import SUDOERS
from DAXXMUSIC.utils.database import is_on_off


# ------------------------------
# Cookies Helper
# ------------------------------
def cookie_txt_file():
    folder_path = f"{os.getcwd()}/cookies"
    filename = f"{os.getcwd()}/cookies/logs.csv"
    txt_files = glob.glob(os.path.join(folder_path, "*.txt"))
    if not txt_files:
        print("⚠️ No .txt cookie files found, continuing without cookies...")
        return None
    cookie_txt_file = random.choice(txt_files)
    with open(filename, "a") as file:
        file.write(f"Chosen File : {cookie_txt_file}\n")
    return f"cookies/{str(cookie_txt_file).split('/')[-1]}"


# ------------------------------
# YouTube Downloader Helper
# ------------------------------
async def ytdl_download(url: str):
    ydl_opts = {
        "quiet": True,
        "format": "bestaudio/best",
        "outtmpl": "%(id)s.%(ext)s",
        "noplaylist": True,
        "nocheckcertificate": True,
        "geo_bypass": True,
        "extract_flat": False,
        "cachedir": False,
    }
    cookie = cookie_txt_file()
    if cookie:
        ydl_opts["cookiefile"] = cookie

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info


# ------------------------------
# Lag Free Audio Player
# ------------------------------
class Call(PyTgCalls):
    def __init__(self, client):
        super().__init__(client)
        self._queue = {}
        self._active = {}

    async def start_call(self, chat_id: int, stream_url: str):
        try:
            print(f"▶️ Starting stream in {chat_id}...")
            await self.join_group_call(
                chat_id,
                InputStream(
                    AudioPiped(
                        stream_url,
                        # Lag free fix settings
                        enable_experimental_lavf=True,
                        reconnect=True,
                        low_buffer=True,
                    )
                ),
            )
            self._active[chat_id] = stream_url
        except NoActiveGroupCall:
            print(f"❌ No active voice chat in {chat_id}")
        except Exception as e:
            print(f"⚠️ Error starting call in {chat_id}: {e}")

    async def stop_call(self, chat_id: int):
        try:
            await self.leave_group_call(chat_id)
            self._active.pop(chat_id, None)
            print(f"⏹️ Stopped stream in {chat_id}")
        except Exception as e:
            print(f"⚠️ Error stopping call: {e}")

    async def change_stream(self, chat_id: int, stream_url: str):
        try:
            await self.change_stream(
                chat_id,
                InputStream(
                    AudioPiped(
                        stream_url,
                        enable_experimental_lavf=True,
                        reconnect=True,
                        low_buffer=True,
                    )
                ),
            )
            self._active[chat_id] = stream_url
            print(f"🔄 Changed stream in {chat_id}")
        except Exception as e:
            print(f"⚠️ Error changing stream: {e}")

    def get_active(self, chat_id: int) -> Union[str, None]:
        return self._active.get(chat_id)


# ------------------------------
# Init
# ------------------------------
DAXX = Call(app)
