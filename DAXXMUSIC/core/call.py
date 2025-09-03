import asyncio
import os
from datetime import datetime, timedelta
from typing import Union

from pyrogram import Client
from pytgcalls import PyTgCalls, StreamType
from pytgcalls.exceptions import (
    AlreadyJoinedError,
    NoActiveGroupCall,
    TelegramServerError,
)
from pytgcalls.types.input_stream import AudioPiped, AudioVideoPiped
from pytgcalls.types.input_stream.quality import HighQualityAudio, MediumQualityVideo

import config
from DAXXMUSIC import LOGGER, app
from DAXXMUSIC.misc import db
from DAXXMUSIC.utils.database import (
    add_active_chat,
    add_active_video_chat,
    get_lang,
    group_assistant,
    is_autoend,
    music_on,
    remove_active_chat,
    remove_active_video_chat,
)
from DAXXMUSIC.utils.exceptions import AssistantErr
from DAXXMUSIC.utils.formatters import check_duration, seconds_to_min, speed_converter

autoend = {}
counter = {}


async def _clear_(chat_id):
    db[chat_id] = []
    await remove_active_video_chat(chat_id)
    await remove_active_chat(chat_id)


class Call:
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

    # ✅ Fix: add start method
    async def start(self):
        if config.STRING1:
            await self.userbot1.start()
            await self.one.start()
        if config.STRING2:
            await self.userbot2.start()
            await self.two.start()
        if config.STRING3:
            await self.userbot3.start()
            await self.three.start()
        if config.STRING4:
            await self.userbot4.start()
            await self.four.start()
        if config.STRING5:
            await self.userbot5.start()
            await self.five.start()
        LOGGER(__name__).info("✅ PyTgCalls Assistants Started Successfully!")

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
        try:
            if config.STRING1:
                await self.one.leave_group_call(chat_id)
            if config.STRING2:
                await self.two.leave_group_call(chat_id)
            if config.STRING3:
                await self.three.leave_group_call(chat_id)
            if config.STRING4:
                await self.four.leave_group_call(chat_id)
            if config.STRING5:
                await self.five.leave_group_call(chat_id)
            await _clear_(chat_id)
        except:
            pass

    async def stream_call(self, link):
        assistant = await group_assistant(self, config.LOGGER_ID)
        await assistant.join_group_call(
            config.LOGGER_ID,
            AudioVideoPiped(link),
            stream_type=StreamType().local_stream,
        )
        await asyncio.sleep(0.2)
        await assistant.leave_group_call(config.LOGGER_ID)

    async def join_call(self, chat_id: int, original_chat_id: int, link, video: Union[bool, str] = None):
        assistant = await group_assistant(self, chat_id)
        language = await get_lang(chat_id)
        _ = language  # keeping for translation use

        if video:
            stream = AudioVideoPiped(link, audio_parameters=HighQualityAudio(), video_parameters=MediumQualityVideo())
        else:
            stream = AudioPiped(link, audio_parameters=HighQualityAudio())

        stream_type = StreamType().live_stream if "live_" in str(link) else StreamType().local_stream

        try:
            await assistant.join_group_call(chat_id, stream, stream_type=stream_type)
        except NoActiveGroupCall:
            raise AssistantErr("No Active Voice Chat Found.")
        except AlreadyJoinedError:
            raise AssistantErr("Assistant already joined.")
        except TelegramServerError:
            raise AssistantErr("Telegram server error. Try again later.")

        await add_active_chat(chat_id)
        await music_on(chat_id)
        if video:
            await add_active_video_chat(chat_id)

        if await is_autoend():
            counter[chat_id] = {}
            users = len(await assistant.get_participants(chat_id))
            if users == 1:
                autoend[chat_id] = datetime.now() + timedelta(minutes=1)


DAXX = Call()
