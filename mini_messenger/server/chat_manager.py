from .storage import InMemoryStorage
from mini_messenger.protocol.types import ChatType
from typing import Optional


class ChatManager:
    def __init__(self, storage: InMemoryStorage, cache: Optional[object] = None):
        self.storage = storage
        # cache должен реализовывать методы get_chat, add_member и, возможно, store_chat
        self.cache = cache
    
    def _get_chat(self, chat_id: int) -> dict | None:
        if self.cache:
            chat = self.cache.get_chat(chat_id)
            if chat is not None:
                return chat
        return self.storage.chats.get(chat_id)
    
    def _save_chat(self, chat_id: int, chat: dict):
        # сохраняем в обоих местах
        self.storage.chats[chat_id] = chat
        if self.cache:
            self.cache.store_chat(chat_id, chat)
    
    def can_send(self, user_id: str, chat_id: int) -> bool:
        chat = self._get_chat(chat_id)
        if not chat:
            return False
        if chat['type'] == ChatType.CHANNEL and chat.get('admin') != user_id:
            return False
        return user_id in chat.get('members', set())
    
    def add_member(self, chat_id: int, user_id: str, inviter_id: str = None) -> bool:
        chat = self._get_chat(chat_id)
        if chat and (chat['type'] != ChatType.CHANNEL or chat.get('admin') == inviter_id):
            members = chat.setdefault('members', set())
            members.add(user_id)
            chat['members'] = members
            self._save_chat(chat_id, chat)
            # если есть cache, оно будет обновлено в _save_chat
            return True
        return False
