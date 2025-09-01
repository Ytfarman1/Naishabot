import asyncio
import os
import re
import json
import glob
import random
import logging
from typing import Union
import aiohttp

import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch

from DAXXMUSIC.utils.database import is_on_off
from DAXXMUSIC.utils.formatters import time_to_seconds
import config


def cookie_txt_file():
    folder_path = f"{os.getcwd()}/cookies"
    filename = f"{os.getcwd()}/cookies/logs.csv"
    txt_files = glob.glob(os.path.join(folder_path, '*.txt'))
    if not txt_files:
        raise FileNotFoundError("No .txt files found in the specified folder.")
    cookie_txt_file = random.choice(txt_files)
    with open(filename, 'a') as file:
        file.write(f'Choosen File : {cookie_txt_file}\n')
    return f"""cookies/{str(cookie_txt_file).split("/")[-1]}"""


async def check_file_size(link):
    async def get_format_info(link):
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "--cookies", cookie_txt_file(),
            "-J",
            link,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            print(f'Error:\n{stderr.decode()}')
            return None
        return json.loads(stdout.decode())

    def parse_size(formats):
        total_size = 0
        for format in formats:
            if 'filesize' in format:
                total_size += format['filesize']
        return total_size

    info = await get_format_info(link)
    if info is None:
        return None
    
    formats = info.get('formats', [])
    if not formats:
        print("No formats found.")
        return None
    
    total_size = parse_size(formats)
    return total_size


async def shell_cmd(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, errorz = await proc.communicate()
    if errorz:
        if "unavailable videos are hidden" in (errorz.decode("utf-8")).lower():
            return out.decode("utf-8")
        else:
            return errorz.decode("utf-8")
    return out.decode("utf-8")


class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.api_key = getattr(config, "YOUTUBE_API_KEY", None)
        self.search_url = "https://www.googleapis.com/youtube/v3/search"
        self.details_url = "https://www.googleapis.com/youtube/v3/videos"
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    # ---------- API BASED SEARCH ----------
    async def search_api(self, query: str, max_results: int = 1):
        if not self.api_key:
            return None
        async with aiohttp.ClientSession() as session:
            params = {
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": max_results,
                "key": self.api_key,
            }
            async with session.get(self.search_url, params=params) as resp:
                data = await resp.json()
                if "items" not in data or not data["items"]:
                    return None
                results = []
                for item in data["items"]:
                    video_id = item["id"]["videoId"]
                    title = item["snippet"]["title"]
                    thumbnail = item["snippet"]["thumbnails"]["high"]["url"]
                    results.append({
                        "video_id": video_id,
                        "title": title,
                        "thumbnail": thumbnail,
                        "link": f"{self.base}{video_id}"
                    })
                return results

    async def details_api(self, video_id: str):
        if not self.api_key:
            return None
        async with aiohttp.ClientSession() as session:
            params = {
                "part": "contentDetails,snippet",
                "id": video_id,
                "key": self.api_key,
            }
            async with session.get(self.details_url, params=params) as resp:
                data = await resp.json()
                if "items" not in data or not data["items"]:
                    return None
                item = data["items"][0]
                title = item["snippet"]["title"]
                thumbnail = item["snippet"]["thumbnails"]["high"]["url"]
                duration = item["contentDetails"]["duration"]
                return {
                    "title": title,
                    "thumbnail": thumbnail,
                    "duration": duration,
                    "video_id": video_id,
                    "link": f"{self.base}{video_id}"
                }

    # ---------- OLD FUNCTIONS (yt-dlp + searchpython) ----------
    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        return bool(re.search(self.regex, link))

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        text = ""
        offset = None
        length = None
        for message in messages:
            if offset:
                break
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        offset, length = entity.offset, entity.length
                        break
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        if offset in (None,):
            return None
        return text[offset : offset + length]

    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]

        # First try API
        if self.api_key:
            vidid = link.replace(self.base, "")
            api_res = await self.details_api(vidid)
            if api_res:
                return api_res["title"], api_res["duration"], 0, api_res["thumbnail"], vidid

        # fallback to python lib
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            vidid = result["id"]
            duration_sec = int(time_to_seconds(duration_min)) if duration_min else 0
        return title, duration_min, duration_sec, thumbnail, vidid

    async def video(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "-g",
            "-f",
            "best[height<=?720][width<=?1280]",
            f"{link}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if stdout:
            return 1, stdout.decode().split("\n")[0]
        else:
            return 0, stderr.decode()

    # बाकी download(), playlist(), track(), formats() etc
    # वही रहेंगे जैसा पहले थे (yt-dlp के साथ)
