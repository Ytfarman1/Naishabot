import asyncio
import os
from datetime import datetime, timedelta
from typing import Union

from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup
from pytgcalls import PyTgCalls, StreamType
from pytgcalls.exceptions import (
    AlreadyJoinedError,
    NoActiveGroupCall,
    TelegramServerError,
)
from pytgcalls.types.input_stream import AudioPiped, AudioVideoPiped
from pytgcalls.types.input_stream.quality import HighQualityAudio, MediumQualityVideo

import config
from DAXXMUSIC import LOGGER, YouTube, app
from DAXXMUSIC.misc import db
from DAXXMUSIC.utils.database import (
    add_active_chat,
    add_active_video_chat,
    get_lang,
    get_loop,
    group_assistant,
    is_autoend,
    music_on,
    remove_active_chat,
    remove_active_video_chat,
    set_loop,
)
from DAXXMUSIC.utils.exceptions import AssistantErr
from DAXXMUSIC.utils.formatters import check_duration, seconds_to_min, speed_converter
from DAXXMUSIC.utils.inline.play import stream_markup
from DAXXMUSIC.utils.stream.autoclear import auto_clean
from DAXXMUSIC.utils.thumbnails import get_thumb
from strings import get_string

autoend = {}
counter = {}


async def _clear_(chat_id):
    db[chat_id] = []
    await remove_active_video_chat(chat_id)
    await remove_active_chat(chat_id)


class Call(PyTgCalls):
    def __init__(self):
        self.userbot1 = Client(
            name="DAXXAss1",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING1),
        )
        self.one = PyTgCalls(self.userbot1, cache_duration=100)

        self.userbot2 = Client(
            name="DAXXAss2",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING2),
        )
        self.two = PyTgCalls(self.userbot2, cache_duration=100)

        self.userbot3 = Client(
            name="DAXXAss3",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING3),
        )
        self.three = PyTgCalls(self.userbot3, cache_duration=100)

        self.userbot4 = Client(
            name="DAXXAss4",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING4),
        )
        self.four = PyTgCalls(self.userbot4, cache_duration=100)

        self.userbot5 = Client(
            name="DAXXAss5",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING5),
        )
        self.five = PyTgCalls(self.userbot5, cache_duration=100)

    async def pause_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        await assistant.pause_stream(chat_id)

    async def resume_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        await assistant.resume_stream(chat_id)

    async def stop_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        try:
            await _clear_(chat_id)
            await assistant.leave_group_call(chat_id)
        except:
            pass

    async def stop_stream_force(self, chat_id: int):
        for client in [self.one, self.two, self.three, self.four, self.five]:
            try:
                await client.leave_group_call(chat_id)
            except:
                pass
        try:
            await _clear_(chat_id)
        except:
            pass

    async def skip_stream(
        self, chat_id: int, link: str, video: Union[bool, str] = None
    ):
        assistant = await group_assistant(self, chat_id)
        if video:
            stream = AudioVideoPiped(
                link,
                audio_parameters=HighQualityAudio(),
                video_parameters=MediumQualityVideo(),
                additional_ffmpeg_parameters="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -bufsize 512k",
            )
        else:
            stream = AudioPiped(
                link,
                audio_parameters=HighQualityAudio(),
                additional_ffmpeg_parameters="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -bufsize 512k",
            )
        await assistant.change_stream(chat_id, stream)

    async def join_call(
        self, chat_id: int, original_chat_id: int, link, video: Union[bool, str] = None
    ):
        assistant = await group_assistant(self, chat_id)
        language = await get_lang(chat_id)
        _ = get_string(language)

        if video:
            stream = AudioVideoPiped(
                link,
                audio_parameters=HighQualityAudio(),
                video_parameters=MediumQualityVideo(),
                additional_ffmpeg_parameters="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -bufsize 512k",
            )
        else:
            stream = AudioPiped(
                link,
                audio_parameters=HighQualityAudio(),
                additional_ffmpeg_parameters="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -bufsize 512k",
            )

        try:
            await assistant.join_group_call(
                chat_id, stream, stream_type=StreamType().pulse_stream
            )
        except NoActiveGroupCall:
            raise AssistantErr(_["call_8"])
        except AlreadyJoinedError:
            raise AssistantErr(_["call_9"])
        except TelegramServerError:
            raise AssistantErr(_["call_10"])

        await add_active_chat(chat_id)
        await music_on(chat_id)
        if video:
            await add_active_video_chat(chat_id)

    async def seek_stream(self, chat_id, file_path, to_seek, duration, mode):
        assistant = await group_assistant(self, chat_id)
        if mode == "video":
            stream = AudioVideoPiped(
                file_path,
                audio_parameters=HighQualityAudio(),
                video_parameters=MediumQualityVideo(),
                additional_ffmpeg_parameters=f"-ss {to_seek} -to {duration} -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -bufsize 512k",
            )
        else:
            stream = AudioPiped(
                file_path,
                audio_parameters=HighQualityAudio(),
                additional_ffmpeg_parameters=f"-ss {to_seek} -to {duration} -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -bufsize 512k",
            )
        await assistant.change_stream(chat_id, stream)

    async def change_stream(self, client, chat_id):
        check = db.get(chat_id)
        if not check:
            return
        queued = check[0]["file"]
        streamtype = check[0]["streamtype"]
        video = True if str(streamtype) == "video" else False

        if video:
            stream = AudioVideoPiped(
                queued,
                audio_parameters=HighQualityAudio(),
                video_parameters=MediumQualityVideo(),
                additional_ffmpeg_parameters="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -bufsize 512k",
            )
        else:
            stream = AudioPiped(
                queued,
                audio_parameters=HighQualityAudio(),
                additional_ffmpeg_parameters="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -bufsize 512k",
            )

        await client.change_stream(chat_id, stream)
DAXX = Call()
