import struct
from crypto.keys import KeyManager
from crypto.e2ee import E2EE
from protocol.types import ChatType

class Session:
    def __init__(self):
        self.user_id = None
        self.current_chat = None
        self.chat_list = {}  # chat_id: {name, type, peer_pubkey?}
        self.keys = {}  # chat_id: shared_secret (для E2EE)
        self.private_key, self.public_key = KeyManager.generate_keypair()
    
    def init_e2ee(self, chat_id: int, peer_pubkey: bytes):
        """Вызывается при создании личного чата"""
        secret = KeyManager.derive_shared_secret(self.private_key, peer_pubkey)
        self.keys[chat_id] = secret
    
    def encrypt_for_chat(self, chat_id: int, plaintext: bytes) -> tuple[bytes, bool]:
        """Возвращает (данные, флаг_шифрования)"""
        chat = self.chat_list.get(chat_id)
        if chat and chat['type'] == ChatType.PRIVATE and chat_id in self.keys:
            return E2EE.encrypt(plaintext, self.keys[chat_id]), True
        return plaintext, False
