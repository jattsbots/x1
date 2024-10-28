# This file is a part of FileStreamBot


import asyncio
from WebStreamer.utils.Translation import Language
from WebStreamer.bot import StreamBot, multi_clients
from WebStreamer.utils.bot_utils import gen_link, validate_user
from WebStreamer.utils.database import Database
from WebStreamer.utils.file_properties import get_file_ids, get_file_info
from WebStreamer.vars import Var
from pyrogram import filters, Client
from pyrogram.errors import FloodWait
from pyrogram.types import Message
from pyrogram.enums.parse_mode import ParseMode
db = Database(Var.DATABASE_URL, Var.SESSION_NAME)

@StreamBot.on_message(
    filters.private
    & (
        filters.document
        | filters.video
        | filters.audio
        | filters.animation
        | filters.voice
        | filters.video_note
        | filters.photo
        | filters.sticker
    ),
    group=4,
)
async def private_receive_handler(bot: Client, message: Message):
    lang = Language(message)
    if not await validate_user(message, lang):
        return
    try:
        ptype=await db.link_available(message.from_user.id)
        if not (ptype):
            return await message.reply_text(lang.LINK_LIMIT_EXCEEDED)

        inserted_id=await db.add_file(get_file_info(message))
        await get_file_ids(False, inserted_id, multi_clients)
        reply_markup, Stream_Text = await gen_link(m=message, _id=inserted_id, name=[StreamBot.username, StreamBot.fname])
        await message.reply_text(
            text=Stream_Text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=reply_markup,
            quote=True
        )
    except FloodWait as e:
        print(f"Sleeping for {str(e.value)}s")
        await asyncio.sleep(e.value)
        await bot.send_message(chat_id=Var.BIN_CHANNEL, text=f"Gᴏᴛ FʟᴏᴏᴅWᴀɪᴛ ᴏғ {str(e.value)}s from [{message.from_user.first_name}](tg://user?id={message.from_user.id})\n\n**𝚄𝚜𝚎𝚛 𝙸𝙳 :** `{str(message.from_user.id)}`", disable_web_page_preview=True, parse_mode=ParseMode.MARKDOWN)

@StreamBot.on_message(filters.command("link") & filters.reply)
async def link_handler(client: Client, message: Message):
    """Handle the link command when replying to a media file."""
    await register_user(client, message)  # Register the user

    reply_msg = message.reply_to_message
    if not reply_msg or not reply_msg.media:
        await message.reply_text("⚠️ Please reply to a media file to generate a link.", quote=True)
        return

    if message.chat.type in ['group', 'supergroup']:
        is_admin = await check_admin_privileges(client, message.chat.id)
        if not is_admin:
            await message.reply_text("🔒 The bot needs admin rights in this group to function properly.", quote=True)
            return

    await process_media_message(client, message, reply_msg)  # Process the media file

 @StreamBot.on_message(filters.private & (filters.document | filters.video | filters.audio | filters.photo), group=4)
async def private_receive_handler(client: Client, message: Message):
    """Handle direct media uploads in private chat."""
    await register_user(client, message)  # Register the user
    await process_media_message(client, message, message)  # Process the media file

async def process_media_message(client: Client, command_message: Message, media_message: Message):
    """Process the media message and generate streaming and download links."""
    try:
        log_msg = await media_message.forward(chat_id=Var.BIN_CHANNEL)  # Forward media to log channel
        stream_link, online_link = await generate_links(log_msg)
        media_name = get_name(log_msg)
        media_size = humanbytes(get_media_file_size(media_message))

        # Create a message with the details
        msg_text = (
            "🔗 <b>Your Links are Ready!</b>\n\n"
            f"📄 <b>File Name:</b> <i>{media_name}</i>\n\n"
            f"📂 <b>File Size:</b> <i>{media_size}</i>\n\n"
            f"📥 <b>Download Link:</b>\n<code>{online_link}</code>\n\n"
            f"🖥️ <b>Watch Now:</b>\n<code>{stream_link}</code>\n\n"
            "⏰ <b>Note:</b> Links are available as long as the bot is active."
        )

        await command_message.reply_text(
            msg_text,
            quote=True,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🖥️ Watch Now", url=stream_link), 
                 InlineKeyboardButton("📥 Download", url=online_link)]
            ])
        )

