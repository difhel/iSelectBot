import datetime
import random
from aiogram import Bot
import aiogram
from aiogram.enums import ParseMode
from bot import strings
from config import Config
from shared import db, typings

config = Config()

bot = Bot(
    token=config.telegram.bot_token,
    parse_mode=ParseMode.MARKDOWN
)

async def check_conditions(
    member: int,
    giveaway: typings.Giveaway
) -> bool:
    # check if the member is a member of every channel
    for channel_id in set(giveaway.channels) | {giveaway.send_to_id}:
        try:
            chat_member = await bot.get_chat_member(channel_id, member)
            if chat_member.status not in ("member", "administrator", "creator"):
                return False
        except aiogram.exceptions.TelegramForbiddenError:
            # bot was removed from one of the channels
            # so we don't check if user is subscribed
            continue
    return True

async def end_giveaway(giveaway: typings.Giveaway) -> str:
    members = giveaway.members
    random.shuffle(members)
    approved_members: list[typings.GiveawayMember] = giveaway.winners
    for member in members:
        if len(approved_members) >= giveaway.winners_count:
            break
        if await check_conditions(member.id, giveaway):
            approved_members.append(member)
    giveaway.status = "end"
    giveaway.winners = approved_members
    message_text = "🎉 Розыгрыш завершен! Победители:\n\n"
    place = 1
    for winner in approved_members:
        message_text += f"{place}. {winner.name} ([{winner.id}](tg://user?id={winner.id}))\n"
        place += 1
    message_text = message_text.strip()

    db.update_giveaway(giveaway)
    db.update_winners_stats(approved_members)
    return message_text

async def add_winners(giveaway: typings.Giveaway, new_winners_count: int) -> str:
    members = list(set(giveaway.members) - set(giveaway.winners))
    random.shuffle(members)
    new_winners: list[typings.GiveawayMember] = []
    for member in members:
        if len(new_winners) >= new_winners_count:
            break
        if await check_conditions(member.id, giveaway):
            new_winners.append(member)
    giveaway.winners = giveaway.winners + new_winners
    if len(new_winners) == 0:
        return (
            "Не нашлось участников, выполнивших условия розыгрыша, "
            "дополнительных победителей нет!"
        )
    message_text = "🎉 Дополнительные победители:\n\n"
    place = 1
    for winner in new_winners:
        message_text += f"{place}. {winner.name} ([{winner.id}](tg://user?id={winner.id}))\n"
        place += 1
    message_text = message_text.strip()
    db.update_giveaway(giveaway)
    db.update_winners_stats(new_winners)
    return message_text

async def scheduled_end_giveaway(
    giveaway_id: str,
    scheduled_date: datetime.datetime | None,
    skip_all_checks: bool = False
) -> None:
    if (giveaway := db.get_giveaway_by_id(giveaway_id)) is None:
        # giveaway was deleted
        return
    if skip_all_checks:
        message = await end_giveaway(giveaway)
        link = f"https://t.me/iselectbot/start?startapp=giveaway_{giveaway.id}"
        await bot.send_message(
            chat_id=giveaway.send_to_id,
            text=message,
            reply_markup=strings.check_results_keyboard(link).as_markup()
        )
    if giveaway.deadline.type != "time":
        return
    deadline_date = datetime.datetime.fromtimestamp(giveaway.deadline.time)
    if deadline_date != scheduled_date:
        # giveaway was rescheduled
        return
    message = await end_giveaway(giveaway)
    link = f"https://t.me/iselectbot/start?startapp=giveaway_{giveaway.id}"
    await bot.send_message(
        chat_id=giveaway.send_to_id,
        text=message,
        reply_markup=strings.check_results_keyboard(link).as_markup()
    )
