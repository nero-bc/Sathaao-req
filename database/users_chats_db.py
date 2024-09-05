# https://github.com/odysseusmax/animated-lamp/blob/master/bot/database/database.py
import motor.motor_asyncio
from info import DATABASE_NAME, DATABASE_URI, IMDB, IMDB_TEMPLATE, MELCOW_NEW_USERS, P_TTI_SHOW_OFF, SINGLE_BUTTON, SPELL_CHECK_REPLY, PROTECT_CONTENT

class Database:
    
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.users
        self.grp = self.db.groups
        self.req = self.db.req
        self.f_channels = self.db.fsub_channels
        self.req_fsub = self.db.req_fsub_ids

    def new_user(self, id, name):
        return dict(
            id = id,
            name = name,
            ban_status=dict(
                is_banned=False,
                ban_reason="",
            ),
        )


    def new_group(self, id, title):
        return dict(
            id = id,
            title = title,
            chat_status=dict(
                is_disabled=False,
                reason="",
            ),
        )

    async def find_join_req(self, id):
        return bool(await self.req.find_one({'id': id}))
        
    async def add_join_req(self, id):
        await self.req.insert_one({'id': id})

    async def del_join_req(self):
        await self.req.drop()

    
    async def add_user(self, id, name):
        user = self.new_user(id, name)
        await self.col.insert_one(user)
    
    async def is_user_exist(self, id):
        user = await self.col.find_one({'id':int(id)})
        return bool(user)
    
    async def total_users_count(self):
        count = await self.col.count_documents({})
        return count
    
    async def remove_ban(self, id):
        ban_status = dict(
            is_banned=False,
            ban_reason=''
        )
        await self.col.update_one({'id': id}, {'$set': {'ban_status': ban_status}})
    
    async def ban_user(self, user_id, ban_reason="No Reason"):
        ban_status = dict(
            is_banned=True,
            ban_reason=ban_reason
        )
        await self.col.update_one({'id': user_id}, {'$set': {'ban_status': ban_status}})

    async def get_ban_status(self, id):
        default = dict(
            is_banned=False,
            ban_reason=''
        )
        user = await self.col.find_one({'id':int(id)})
        if not user:
            return default
        return user.get('ban_status', default)

    async def get_all_users(self):
        return self.col.find({})
    

    async def delete_user(self, user_id):
        await self.col.delete_many({'id': int(user_id)})


    async def get_banned(self):
        users = self.col.find({'ban_status.is_banned': True})
        chats = self.grp.find({'chat_status.is_disabled': True})
        b_chats = [chat['id'] async for chat in chats]
        b_users = [user['id'] async for user in users]
        return b_users, b_chats
    


    async def add_chat(self, chat, title):
        chat = self.new_group(chat, title)
        await self.grp.insert_one(chat)
    

    async def get_chat(self, chat):
        chat = await self.grp.find_one({'id':int(chat)})
        return False if not chat else chat.get('chat_status')
    

    async def re_enable_chat(self, id):
        chat_status=dict(
            is_disabled=False,
            reason="",
            )
        await self.grp.update_one({'id': int(id)}, {'$set': {'chat_status': chat_status}})
        
    async def update_settings(self, id, settings):
        await self.grp.update_one({'id': int(id)}, {'$set': {'settings': settings}})
        
    
    async def get_settings(self, id):
        default = {
            'button': SINGLE_BUTTON,
            'botpm': P_TTI_SHOW_OFF,
            'file_secure': PROTECT_CONTENT,
            'imdb': IMDB,
            'spell_check': SPELL_CHECK_REPLY,
            'welcome': MELCOW_NEW_USERS,
            'template': IMDB_TEMPLATE
        }
        chat = await self.grp.find_one({'id':int(id)})
        if chat:
            return chat.get('settings', default)
        return default
    

    async def disable_chat(self, chat, reason="No Reason"):
        chat_status=dict(
            is_disabled=True,
            reason=reason,
            )
        await self.grp.update_one({'id': int(chat)}, {'$set': {'chat_status': chat_status}})
    

    async def total_chat_count(self):
        count = await self.grp.count_documents({})
        return count
    

    async def get_all_chats(self):
        return self.grp.find({})


    async def get_db_size(self):
        return (await self.db.command("dbstats"))['dataSize']
    async def get_fsub_channels(self):
        doc = await self.f_channels.find_one({})
        if doc is None:
            return []
        return doc['channels']
    
    async def add_fsub_channels(self , channel_id ,  bulk=False):
        try: 
            if bulk:
                return await self.f_channels.update_one({} , {'$set' : {'channels' : channel_id}})
            channels = await self.get_fsub_channels()
            if not channel_id in channels:
                channels.append(channel_id)
            else:
                return False
            is_updated = await self.f_channels.update_one({} , {'$set' : {'channels' : channels} } , upsert=True)
            if is_updated:
                return True
            False
        except Exception as e:
            print('error in add_fsub_channels',e)
            return False
    async def del_fsub_channels(self , channel_id= None , bulk=False):

        try:
            if bulk:
                is_deleted = await self.f_channels.delete_many({})
                if is_deleted:
                    return True
                return False
            channels = await self.get_fsub_channels()
            if not channel_id in channels:
                return False
            channels.remove(channel_id)
            is_updated = await self.f_channels.update_one({} , {'$set' : {'channels' : channels}},  upsert=True)
            if is_updated:
                return True
            return False
        except Exception as e:
            print('error in del_fsub_channels',e)
            return False
    async def add_fsub_join_req(self , chat_id , user_id):
        try:
            req = dict(
                chat_id = int(chat_id),
                user_id = int(user_id)
            )
            await self.req_fsub.insert_one(req)
            return True
        except Exception as e:
            print('error in add_fsub_join_req',e)
            return False
    async def get_fsub_join_req(self , chat_id , user_id):
        try:
            req = dict(
                chat_id = int(chat_id),
                user_id = int(user_id)
            )
            is_req = await self.req_fsub.find_one(req)
            return True if is_req else False
        except Exception as e:
            return False
        
    async def remove_fsub_join_req(self , chat_id , user_id):
        try:
            req = dict(
                chat_id = int(chat_id),
                user_id = int(user_id)
            )
            is_deleted = await self.req_fsub.delete_one(req)
            if is_deleted:
                return True
            return False
        except Exception as e:
            return False
db = Database(DATABASE_URI, DATABASE_NAME)
