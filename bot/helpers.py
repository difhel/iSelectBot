import hashlib
import random
from datetime import datetime, timedelta, timezone
import typing
import aiogram
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery, User
from bot.scheduler import SchedulerWrapper
from config import Config
from shared import avatars, db, typings
from shared.giveaway_manager import scheduled_end_giveaway

config = Config()
bot = aiogram.Bot(
    token=config.telegram.bot_token,
    parse_mode=ParseMode.MARKDOWN
)

MsgOrCbType = Message | CallbackQuery

async def prepare_message(msg_or_callback: MsgOrCbType, delete_original_message: bool = False) -> Message:
    if isinstance(msg_or_callback, CallbackQuery):
        await msg_or_callback.answer()
        if delete_original_message and msg_or_callback.message is not None:
            await msg_or_callback.message.delete()
        if not isinstance(msg_or_callback.message, Message):
            raise ValueError("Callback.message is not a message")
        return msg_or_callback.message
    return msg_or_callback

async def prepare_message_with_user(
    msg_or_callback: MsgOrCbType,
    delete_original_message: bool = False
) -> tuple[Message, User]:
    if isinstance(msg_or_callback, CallbackQuery):
        await msg_or_callback.answer()
        if delete_original_message and msg_or_callback.message is not None:
            await msg_or_callback.message.delete()
        if not isinstance(msg_or_callback.message, Message):
            raise ValueError("Callback.message is not a message")
        return (
            msg_or_callback.message,
            msg_or_callback.from_user
        )
    return (
        msg_or_callback,
        msg_or_callback.from_user
    )

async def is_bot_admin(bot: aiogram.Bot, channel: typings.Channel | None) -> bool:
    """
    Async function to check if the bot is an admin in the given chat.

    Args:
        bot (aiogram.Bot): bot instance
        channel (typings.Channel | None): the channel
    Returns:
        bool: True if the bot is an admin in the given chat, False otherwise
    """
    if channel is None:
        return False
    try:
        chat_member = await bot.get_chat_member(channel.id, bot.id)
        if chat_member.status not in ("administrator", "creator"):
            return False
        if not chat_member.can_post_messages:
            return False
        return True
    except aiogram.exceptions.TelegramForbiddenError:
        return False

async def parse_mention(bot: aiogram.Bot, mention: str) -> typings.Channel | None:
    """
    Function to parse the mention and return the channel/group id.

    Args:
        bot (aiogram.Bot): bot instance
        mention (str): channel or group mention
    Returns:
        int: channel id
    """
    if not mention.startswith("@"):
        return None
    try:
        chat = await bot.get_chat(mention)
        if chat.type in {"channel", "group", "supergroup"}:
            link = f"https://t.me/{chat.username}" if chat.username is not None else None
            await avatars.download_channel_avatar(bot, chat, config.fs.cached_avatars_path)
            return typings.Channel(
                _id=chat.id,
                channel_name=chat.title,
                admin=None,
                link=link
            )
    except aiogram.exceptions.TelegramAPIError:
        return None
    return None

async def get_channel_by_tg_id(bot: aiogram.Bot, channel_id: int) -> typings.Channel | None:
    try:
        chat = await bot.get_chat(channel_id)
        if chat.type in {"channel", "group", "supergroup"}:
            link = f"https://t.me/{chat.username}" if chat.username is not None else None
            await avatars.download_channel_avatar(bot, chat, config.fs.cached_avatars_path)
            return typings.Channel(
                _id=chat.id,
                channel_name=chat.title,
                admin=None,
                link=link
            )
    except aiogram.exceptions.TelegramAPIError:
        return None
    return None


def get_time_str_from_timestamp(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp).strftime('%d.%m.%Y %H:%M')

def parse_time(time_str: str) -> datetime | None:
    try:
        parsed_time = datetime.strptime(time_str, '%d.%m.%Y %H:%M')
        return parsed_time
    except ValueError:
        return None

def get_current_time() -> int:
    return int(datetime.now().timestamp())

def generate_giveaway_id() -> str:
    """
    - Мама, можно нам домой UUIDv4?
    - Нет, у нас дома уже есть UUIDv4
    UUIDv4 дома:
    """
    return hashlib.sha256(str(
        datetime.now().timestamp() + random.randint(-100000, 100000)
    ).encode()).hexdigest()[:6]

def get_giveaway_by_data(data: dict[str, typing.Any], user_id: int) -> typings.Giveaway:
    if data["end_type"] == "time":
        deadline = typings.TimeDeadline(
            type="time",
            time=data["end_time"]
        )
    else:
        deadline = typings.MembersDeadline(
            type="members",
            members=data["end_members"]
        )
    if data["publish_time"] == 0:
        data["publish_time"] = get_current_time() + 10
    giveaway = typings.Giveaway(
        _id=generate_giveaway_id(),
        created=get_current_time(),
        publish_time=data["publish_time"],
        button_text=data["button_text"],
        admin=user_id,
        channels=data["channels"],
        send_to_id=data["send_to_id"],
        members=[],
        ip_counter={},
        status="waiting",
        winners=[],
        winners_count=data["winners_count"],
        msg_ids=data["msg_ids"],
        deadline=deadline,
        top_msg_id=None,
        preview_text=data["preview_text"]
    )
    return giveaway

def schedule_giveaway(giveaway: typings.Giveaway, skip_publishing: bool = False) -> None:
    """Function to schedule giveaway publishing and finishing.

    Args:
        giveaway (typings.Giveaway): the giveaway
    """
    scheduler = SchedulerWrapper()
    # schedule publishing
    if not skip_publishing:
        scheduler.add_job(
            publish_giveaway,
            "date",
            run_date=datetime.fromtimestamp(giveaway.publish_time),
            args=(giveaway, False)
        )
    # schedule ending
    if giveaway.deadline.type != "time":
        return
    scheduler.add_job(
        scheduled_end_giveaway,
        "date",
        run_date=datetime.fromtimestamp(giveaway.deadline.time),
        args=(giveaway.id, datetime.fromtimestamp(giveaway.deadline.time))
    )

def get_giveaway_keyboard(giveaway: typings.Giveaway, test: bool) -> aiogram.types.InlineKeyboardMarkup:
    if test:
        return aiogram.utils.keyboard.InlineKeyboardBuilder().add(
            aiogram.utils.keyboard.InlineKeyboardButton(
                text=giveaway.button_text,
                callback_data="magic"
            )
        ).as_markup()
    return aiogram.utils.keyboard.InlineKeyboardBuilder().add(
        aiogram.utils.keyboard.InlineKeyboardButton(
            text=giveaway.button_text,
            url=f"https://t.me/iselectbot/start?startapp={giveaway.id}"
        )
    ).as_markup()

async def publish_giveaway(
    giveaway: typings.Giveaway,
    test_mode: bool = True
) -> None:
    peer = giveaway.admin if test_mode else giveaway.send_to_id
    if len(giveaway.msg_ids) == 1:
        top_msg_id = await bot.copy_message(
            chat_id=peer,
            from_chat_id=giveaway.admin,
            message_id=giveaway.msg_ids[-1],
            reply_markup=get_giveaway_keyboard(giveaway, test_mode)
        )
    else:
        top_msg_id = (await bot.copy_messages(
            chat_id=peer,
            from_chat_id=giveaway.admin,
            message_ids=giveaway.msg_ids[:-1],
            remove_caption=True
        ))[0]
        await bot.copy_message(
            chat_id=peer,
            from_chat_id=giveaway.admin,
            message_id=giveaway.msg_ids[-1],
            reply_markup=get_giveaway_keyboard(giveaway, test_mode)
        )
    if not test_mode:
        giveaway.top_msg_id = top_msg_id.message_id
        giveaway.status = "start"
        db.update_giveaway(giveaway)

def get_message_link(giveaway: typings.Giveaway) -> str | None:
    owner = db.get_channel_by_id(giveaway.send_to_id)
    message_link = None
    if giveaway.top_msg_id is not None:
        if owner.link is None:
            # private channel
            message_link = f"https://t.me/c/{str(owner.id).replace('-100', '')}/{giveaway.top_msg_id}"
        else:
            message_link = f"{owner.link}/{giveaway.top_msg_id}"
    return message_link
