from .storage import InMemoryStorage
from protocol.types import ChatType

class ChatManager:
    def __init__(self, storage: InMemoryStorage):
        self.storage = storage
    
    def can_send(self, user_id: str, chat_id: int) -> bool:
        chat = self.storage.chats.get(chat_id)
        if not chat:
            return False
        if chat['type'] == ChatType.CHANNEL and chat['admin'] != user_id:
            return False
        return user_id in chat['members']
    
    def add_member(self, chat_id: int, user_id: str, inviter_id: str = None):
        chat = self.storage.chats.get(chat_id)
        if chat and (chat['type'] != ChatType.CHANNEL or chat['admin'] == inviter_id):
            chat['members'].add(user_id)
            return True
        return False
