import os
import logging
import random
import asyncio
from Script import script
from pyrogram import Client, filters, enums 
from pyrogram.errors import ChatAdminRequired, FloodWait, InputUserDeactivated, UserNotParticipant, FloodWait, UserIsBlocked, PeerIdInvalid
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup , Message , ChatJoinRequest , ChatMemberUpdated
from database.ia_filterdb import Media, get_file_details, unpack_new_file_id
from database.users_chats_db import db
from info import AUTO_DEL_TIME,  CHANNELS, ADMINS, AUTH_CHANNEL, LOG_CHANNEL, PICS, BATCH_FILE_CAPTION, CUSTOM_FILE_CAPTION, PROTECT_CONTENT, REQ_CHANNEL
from utils import get_settings, get_size, save_group_settings, temp
from database.connections_mdb import active_connection
import re
import json
import base64
logger = logging.getLogger(__name__)

BATCH_FILES = {}

@Client.on_chat_join_request()
async def join_req_check(client: Client, message: ChatJoinRequest):
    channels = await db.get_fsub_channels()
    if not channels:
        return
    if message.chat.id in channels:
        return await db.add_fsub_join_req(message.chat.id , message.from_user.id)
    else: return

@Client.on_chat_member_updated()
async def on_chat_member_update(client: Client, message: ChatMemberUpdated):
    if message.new_chat_member and message.new_chat_member.status in ["member", "administrator"]:
        await db.remove_fsub_join_req(message.chat.id, message.from_user.id)


@Client.on_message(filters.command("add_fsub") & filters.incoming & filters.user(ADMINS))
async def add_fsub(client, message: Message):
    try:
        channel_id = int(message.command[1])
    except:        
        return await message.reply_text("Give me a channel id")
    is_added = await db.add_fsub_channels(channel_id)
    return await message.reply_text(f"Added {channel_id} to fsub list") if is_added else await message.reply_text("Already added")
@Client.on_message(filters.command("del_fsub") & filters.incoming & filters.user(ADMINS))
async def del_fsub(client, message: Message):
    try:
        channel_id = int(message.command[1])
    except:        
        return await message.reply_text("Give me a channel id")
    is_added = await db.del_fsub_channels(channel_id)
    return await message.reply_text(f"Removed {channel_id} to fsub list") if is_added else await message.reply_text("Id not found In DB") 

@Client.on_message(filters.command('del_bulk_fsub') & filters.user(ADMINS) & filters.incoming)
async def del_bulk_fsub(client, message):
    is_del = await db.del_fsub_channels(bulk=True)
    if is_del:
        return await message.reply_text("Removed all fsub list")
    else:
        return await message.reply_text("No fsub list found")
@Client.on_message(filters.command('add_bulk_fsub') & filters.incoming & filters.user(ADMINS))
async def add_bulk_fsub(client, message):
    if len(message.command) < 2:
        return await message.reply_text('Please provide a lists of channel ids separated by space')
    channel_list = message.text.split(None, 1)[1].split(' ')
    try:
        channel_list = list(map(int, channel_list))
    except ValueError:
        return await message.reply_text('Invalid channel ID.Please provide a lists of channel ids separated by space')
    is_added = await db.add_fsub_channels(channel_list , bulk=True)
    if is_added:
        return await message.reply_text(f"Added {', '.join(map(str, channel_list))} to fsub list")
    else:
        return await message.reply_text("Some channel ids are invalid or already added")
@Client.on_message(filters.command('fsub_channels') & filters.user(ADMINS) & filters.incoming)
async def fsub_channels(client, message):
    channels = await db.get_fsub_channels()
    if len(channels) == 0:
        return await message.reply_text("No fsub channels found")
    channels_list = '\n'.join(map(str, channels))
    await message.reply_text(f"**Fsub Channels:**\n\n{channels_list}")

async def is_req_subscribed(bot: Client, query: Message , command):
    try:
        channels = await db.get_fsub_channels()
        if len(channels) == 0:
            return True
        for channel in channels:
            try:
                if await db.get_fsub_join_req(channel , query.from_user.id):
                    continue
                user = await bot.get_chat_member(int(channel), query.from_user.id)
                if user.status == enums.ChatMemberStatus.BANNED:
                    await query.reply_text("Sorry. You're Banned.Contact Admin : @Akv_Contact")
                    return False
            except UserNotParticipant:
                invite_link = await bot.create_chat_invite_link(channel, creates_join_request=True)
                join = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Jᴏɪɴ ɴᴏᴡ", url=invite_link.invite_link)],
                    [
                     InlineKeyboardButton("📥 ɢᴇᴛ ʏᴏᴜʀ ғɪʟᴇ 📥", callback_data=f'isJoined#{command}#{channel}')
                    ]])
                await query.reply_text("**ғɪʀꜱᴛ ᴊᴏɪɴ ᴏᴜʀ ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ ᴛʜᴇɴ ʏᴏᴜ ᴡɪʟʟ ɢᴇᴛ ᴍᴏᴠɪᴇ, ᴏᴛʜᴇʀᴡɪꜱᴇ ʏᴏᴜ ᴡɪʟʟ ɴᴏᴛ ɢᴇᴛ ɪᴛ🙁\n\nफ़ाइल लेनें के लिए सबसे पहले आपको हमारा चैनल ज्वाइन करना होगा अन्यथा Bot फ़ाइल नहीं देगा 🤖**", reply_markup=join)
                return False
        if user.status == enums.ChatMemberStatus.BANNED:return False
        return True
    except Exception as e:
        print(e) 
        return True


@Client.on_message(filters.command("start") & filters.incoming)
async def start(client: Client, message : Message):
    justJoind = False
    try : 
        justJoind = message.command[1].startswith("nkdsnkjn")
        if justJoind:
            message.command[1] = message.command[1].replace("nkdsnkjn_", "")
            justJoind = True
    except: pass 
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        buttons = [
            [
                InlineKeyboardButton("ℹ️ 𝙷𝚎𝚕𝚙", url="https://t.me/helloobrro"),
                InlineKeyboardButton("➡️@SathAao 🇮🇳", url=f"https://t.me/SathAao")
            ]
            ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply(script.START_TXT.format(message.from_user.mention if message.from_user else message.chat.title, temp.U_NAME, temp.B_NAME), reply_markup=reply_markup)
        await asyncio.sleep(2) # 😢 https://github.com/EvamariaTG/EvaMaria/blob/master/plugins/p_ttishow.py#L17 😬 wait a bit, before checking.
        if not await db.get_chat(message.chat.id):
            total=await client.get_chat_members_count(message.chat.id)
            await client.send_message(LOG_CHANNEL, script.LOG_TEXT_G.format(message.chat.title, message.chat.id, total, "Unknown"))       
            await db.add_chat(message.chat.id, message.chat.title)
        return 
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        await client.send_message(LOG_CHANNEL, script.LOG_TEXT_P.format(message.from_user.id, message.from_user.mention))
    if len(message.command) != 2:
        buttons = [[
            InlineKeyboardButton('➕ Add me to your group ➕', url=f'http://t.me/{temp.U_NAME}?startgroup=true')
            ],
            [
            InlineKeyboardButton('➡️@SathAao 🇮🇳', url=f'https://t.me/SathAao')
            ],
            [
            InlineKeyboardButton('ℹ️ 𝙷𝚎𝚕𝚙', callback_data='help'),
            InlineKeyboardButton('😊 𝙰𝚋𝚘𝚞𝚝', callback_data='about')
        ]]
        
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_photo(
            photo=random.choice(PICS),
            caption=script.START_TXT.format(message.from_user.mention, temp.U_NAME, temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        return

    if len(message.command) == 2 and message.command[1] in ["subscribe", "error", "okay", "help", "start", "hehe"]:
        if message.command[1] == "subscribe":
            await ForceSub(client, message)
            return

        buttons = [[
            InlineKeyboardButton('➕ Add me to your group ➕', url=f'http://t.me/{temp.U_NAME}?startgroup=true')
            ],
            [
            InlineKeyboardButton(' ➡️@SathAao 🇮🇳 ', url=f'https://t.me/SathAao')
            ],
            [
            InlineKeyboardButton('ℹ️ 𝙷𝚎𝚕𝚙', callback_data='help'),
            InlineKeyboardButton('😊 𝙰𝚋𝚘𝚞𝚝', callback_data='about')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_photo(
            photo=random.choice(PICS),
            caption=script.START_TXT.format(message.from_user.mention, temp.U_NAME, temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        return

    kk, file_id = message.command[1].split("_", 1) if "_" in message.command[1] else (False, False)
    pre = ('checksubp' if kk == 'filep' else 'checksub') if kk else False
    if not justJoind:
        if not await is_req_subscribed(client, message , message.command[1]):
            return
    data = message.command[1]
    if not file_id:
        file_id = data

    if data.split("-", 1)[0] == "BATCH":
        sts = await message.reply("Please wait")
        file_id = data.split("-", 1)[1]
        msgs = BATCH_FILES.get(file_id)
        if not msgs:
            file = await client.download_media(file_id)
            try: 
                with open(file) as file_data:
                    msgs=json.loads(file_data.read())
            except:
                await sts.edit("FAILED")
                return await client.send_message(LOG_CHANNEL, "UNABLE TO OPEN FILE.")
            os.remove(file)
            BATCH_FILES[file_id] = msgs
        for msg in msgs:
            title = msg.get("title")
            size=get_size(int(msg.get("size", 0)))
            f_caption=msg.get("caption", "")
            if BATCH_FILE_CAPTION:
                try:
                    f_caption=BATCH_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
                except Exception as e:
                    logger.exception(e)
                    f_caption=f_caption
            if f_caption is None:
                f_caption = f"{title}"
            try:
                await client.send_cached_media(
                    chat_id=message.from_user.id,
                    file_id=msg.get("file_id"),
                    caption=f_caption,
                    protect_content=msg.get('protect', False),
                    )
            except FloodWait as e:
                await asyncio.sleep(e.x)
                logger.warning(f"Floodwait of {e.x} sec.")
                await client.send_cached_media(
                    chat_id=message.from_user.id,
                    file_id=msg.get("file_id"),
                    caption=f_caption,
                    reply_markup=InlineKeyboardMarkup( [ [InlineKeyboardButton("🍿 बेजुबानों की एक अनकही दास्तां 🍿", url="https://t.me/SathAao/21")] ] ),
                    protect_content=msg.get('protect', False),
                    )
            except Exception as e:
                logger.warning(e, exc_info=True)
                continue
            await asyncio.sleep(1) 
        await sts.delete()
        return
    elif data.split("-", 1)[0] == "DSTORE":
        sts = await message.reply("Please wait")
        b_string = data.split("-", 1)[1]
        decoded = (base64.urlsafe_b64decode(b_string + "=" * (-len(b_string) % 4))).decode("ascii")
        try:
            f_msg_id, l_msg_id, f_chat_id, protect = decoded.split("_", 3)
        except:
            f_msg_id, l_msg_id, f_chat_id = decoded.split("_", 2)
            protect = "/pbatch" if PROTECT_CONTENT else "batch"
        diff = int(l_msg_id) - int(f_msg_id)
        async for msg in client.iter_messages(int(f_chat_id), int(l_msg_id), int(f_msg_id)):
            if msg.media:
                media = getattr(msg, msg.media)
                if BATCH_FILE_CAPTION:
                    try:
                        f_caption=BATCH_FILE_CAPTION.format(file_name=getattr(media, 'file_name', ''), file_size=getattr(media, 'file_size', ''), file_caption=getattr(msg, 'caption', ''))
                    except Exception as e:
                        logger.exception(e)
                        f_caption = getattr(msg, 'caption', '')
                else:
                    media = getattr(msg, msg.media)
                    file_name = getattr(media, 'file_name', '')
                    f_caption = getattr(msg, 'caption', file_name)
                try:
                    await msg.copy(message.chat.id, caption=f_caption, protect_content=True if protect == "/pbatch" else False)
                except FloodWait as e:
                    await asyncio.sleep(e.x)
                    await msg.copy(message.chat.id, caption=f_caption, protect_content=True if protect == "/pbatch" else False)
                except Exception as e:
                    logger.exception(e)
                    continue
            elif msg.empty:
                continue
            else:
                try:
                    await msg.copy(message.chat.id, protect_content=True if protect == "/pbatch" else False)
                except FloodWait as e:
                    await asyncio.sleep(e.x)
                    await msg.copy(message.chat.id, protect_content=True if protect == "/pbatch" else False)
                except Exception as e:
                    logger.exception(e)
                    continue
            await asyncio.sleep(1) 
        return await sts.delete()
        

    files_ = await get_file_details(file_id)           
    if not files_:
         # Decode data
        try:
            decoded_data = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
            pre, file_id = decoded_data.decode("utf-8").split("_", 1)
        except UnicodeDecodeError as e:
            print(f"UnicodeDecodeError: {e}")
            return

        try:
            msg = await client.send_cached_media(
                chat_id=message.from_user.id,
                file_id=file_id,
                protect_content=True if pre == 'filep' else False,
                )
            filetype = msg.media
            file = getattr(msg, filetype)
            title = file.file_name
            size=get_size(file.file_size)
            f_caption = f"<code>{title}</code>"
            if CUSTOM_FILE_CAPTION:
                try:
                    f_caption=CUSTOM_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='')
                except:
                    return
            await msg.edit_caption(f_caption)
            return
        except:
            pass
        return await message.reply('No such file exist.')
    files = files_[0]
    title = files.file_name
    size=get_size(files.file_size)
    f_caption=files.caption
    if CUSTOM_FILE_CAPTION:
        try:
            f_caption=CUSTOM_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
        except Exception as e:
            logger.exception(e)
            f_caption=f_caption
    if f_caption is None:
        f_caption = f"{files.file_name}"
    try:
        msgToDel = await client.send_cached_media(
            chat_id=message.from_user.id,
            file_id=file_id,
            caption=f_caption,
         
            reply_markup=InlineKeyboardMarkup( [ [InlineKeyboardButton("🍿 बेजुबानों की एक अनकही दास्तां 🍿", url="https://t.me/SathAao/21")] ] ),
            protect_content=True if pre == 'filep' else False,
        )    
        delAlertMsg = await message.reply(
            "This File Will be Deleted Automatically After {} Minutes.".format(AUTO_DEL_TIME),
             reply_to_message_id=msgToDel.id
        )
        await asyncio.sleep(AUTO_DEL_TIME * 60 * 2)
        await msgToDel.delete()
        await delAlertMsg.edit(
            "File Deleted Successfully."
            ,reply_markup=InlineKeyboardMarkup( [ [InlineKeyboardButton("🍿 बेजुबानों की एक अनकही दास्तां 🍿", url="https://t.me/SathAao/21")] ] ),

        )
    except Exception as e:
        await client.send_message(
                chat_id=LOG_CHANNEL, 
                text=f"🔔 #Error\n\nBot is unable to send files to user : {message.from_user.mention}\n\nError: {e}"
        )
                    

@Client.on_message(filters.command('channel') & filters.user(ADMINS))
async def channel_info(bot, message):
           
    """Send basic information of channel"""
    if isinstance(CHANNELS, (int, str)):
        channels = [CHANNELS]
    elif isinstance(CHANNELS, list):
        channels = CHANNELS
    else:
        raise ValueError("Unexpected type of CHANNELS")

    text = '📑 **Indexed channels/groups**\n'
    for channel in channels:
        chat = await bot.get_chat(channel)
        if chat.username:
            text += '\n@' + chat.username
        else:
            text += '\n' + chat.title or chat.first_name

    text += f'\n\n**Total:** {len(CHANNELS)}'

    if len(text) < 4096:
        await message.reply(text)
    else:
        file = 'Indexed channels.txt'
        with open(file, 'w') as f:
            f.write(text)
        await message.reply_document(file)
        os.remove(file)


@Client.on_message(filters.command('logs') & filters.user(ADMINS))
async def log_file(bot, message):
    """Send log file"""
    try:
        await message.reply_document('TelegramBot.log')
    except Exception as e:
        await message.reply(str(e))

@Client.on_message(filters.command('delete') & filters.user(ADMINS))
async def delete(bot, message):
    """Delete file from database"""
    reply = message.reply_to_message
    if reply and reply.media:
        msg = await message.reply("Processing...⏳", quote=True)
    else:
        await message.reply('Reply to file with /delete which you want to delete', quote=True)
        return

    for file_type in ("document", "video", "audio"):
        media = getattr(reply, file_type, None)
        if media is not None:
            break
    else:
        await msg.edit('This is not supported file format')
        return
    
    file_id, file_ref = unpack_new_file_id(media.file_id)

    result = await Media.collection.delete_one({
        '_id': file_id,
    })
    if result.deleted_count:
        await msg.edit('File is successfully deleted from database')
    else:
        file_name = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name))
        result = await Media.collection.delete_many({
            'file_name': file_name,
            'file_size': media.file_size,
            'mime_type': media.mime_type
            })
        if result.deleted_count:
            await msg.edit('File is successfully deleted from database')
        else:
            # files indexed before https://github.com/EvamariaTG/EvaMaria/commit/f3d2a1bcb155faf44178e5d7a685a1b533e714bf#diff-86b613edf1748372103e94cacff3b578b36b698ef9c16817bb98fe9ef22fb669R39 
            # have original file name.
            result = await Media.collection.delete_many({
                'file_name': media.file_name,
                'file_size': media.file_size,
                'mime_type': media.mime_type
            })
            if result.deleted_count:
                await msg.edit('File is successfully deleted from database')
            else:
                await msg.edit('File not found in database')


@Client.on_message(filters.command('deleteall') & filters.user(ADMINS))
async def delete_all_index(bot, message):
    await message.reply_text(
        'This will delete all indexed files.\nDo you want to continue??',
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="YES", callback_data="autofilter_delete"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="CANCEL", callback_data="close_data"
                    )
                ],
            ]
        ),
        quote=True,
    )


@Client.on_callback_query(filters.regex(r'^autofilter_delete'))
async def delete_all_index_confirm(bot, message):
    await Media.collection.drop()
    await message.answer('Piracy Is Crime')
    await message.message.edit('Succesfully Deleted All The Indexed Files.')


@Client.on_message(filters.command('settings'))
async def settings(client, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"You are anonymous admin. Use /connect {message.chat.id} in PM")
    chat_type = message.chat.type

    if chat_type == enums.ChatType.PRIVATE:
        grpid = await active_connection(str(userid))
        if grpid is not None:
            grp_id = grpid
            try:
                chat = await client.get_chat(grpid)
                title = chat.title
            except:
                await message.reply_text("Make sure I'm present in your group!!", quote=True)
                return
        else:
            await message.reply_text("I'm not connected to any groups!", quote=True)
            return

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title

    else:
        return

    st = await client.get_chat_member(grp_id, userid)
    if (
            st.status != enums.ChatMemberStatus.ADMINISTRATOR
            and st.status != enums.ChatMemberStatus.OWNER
            and str(userid) not in ADMINS
    ):
        return

    settings = await get_settings(grp_id)

    if settings is not None:
        buttons = [
            [
                InlineKeyboardButton(
                    'Filter Button',
                    callback_data=f'setgs#button#{settings["button"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    'Single' if settings["button"] else 'Double',
                    callback_data=f'setgs#button#{settings["button"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'Bot PM',
                    callback_data=f'setgs#botpm#{settings["botpm"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✅ Yes' if settings["botpm"] else '❌ No',
                    callback_data=f'setgs#botpm#{settings["botpm"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'File Secure',
                    callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✅ Yes' if settings["file_secure"] else '❌ No',
                    callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'IMDB',
                    callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✅ Yes' if settings["imdb"] else '❌ No',
                    callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'Spell Check',
                    callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✅ Yes' if settings["spell_check"] else '❌ No',
                    callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'Welcome',
                    callback_data=f'setgs#welcome#{settings["welcome"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✅ Yes' if settings["welcome"] else '❌ No',
                    callback_data=f'setgs#welcome#{settings["welcome"]}#{grp_id}',
                ),
            ],
        ]

        reply_markup = InlineKeyboardMarkup(buttons)

        await message.reply_text(
            text=f"<b>Change Your Settings for {title} As Your Wish ⚙</b>",
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            parse_mode=enums.ParseMode.HTML,
            reply_to_message_id=message.id
        )



@Client.on_message(filters.command('set_template'))
async def save_template(client, message):
    sts = await message.reply("Checking template")
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"You are anonymous admin. Use /connect {message.chat.id} in PM")
    chat_type = message.chat.type

    if chat_type == enums.ChatType.PRIVATE:
        grpid = await active_connection(str(userid))
        if grpid is not None:
            grp_id = grpid
            try:
                chat = await client.get_chat(grpid)
                title = chat.title
            except:
                await message.reply_text("Make sure I'm present in your group!!", quote=True)
                return
        else:
            await message.reply_text("I'm not connected to any groups!", quote=True)
            return

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title

    else:
        return

    st = await client.get_chat_member(grp_id, userid)
    if (
            st.status != enums.ChatMemberStatus.ADMINISTRATOR
            and st.status != enums.ChatMemberStatus.OWNER
            and str(userid) not in ADMINS
    ):
        return

    if len(message.command) < 2:
        return await sts.edit("No Input!!")
    template = message.text.split(" ", 1)[1]
    await save_group_settings(grp_id, 'template', template)
    await sts.edit(f"Successfully changed template for {title} to\n\n{template}")
