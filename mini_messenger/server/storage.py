from collections import defaultdict
import uuid

class InMemoryStorage:
    def __init__(self):
        self.users = {}  # conn: {user_id, public_key, current_chat}
        self.chats = {}  # chat_id: {type, name, members(set), messages[]}
        self.user_keys = {}  # user_id: {private_key, public_key}
    
    def create_chat(self, chat_type: int, creator_id: str, name: str = None):
        chat_id = uuid.uuid4().int & 0xFFFFFFFF  # 4-байтный ID
        self.chats[chat_id] = {
            'type': chat_type,
            'name': name or f"Chat_{chat_id}",
            'members': {creator_id},
            'admin': creator_id if chat_type == 3 else None,  # Только для каналов
            'messages': []
        }
        return chat_id
