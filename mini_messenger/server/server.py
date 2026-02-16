import asyncio
from .storage import InMemoryStorage
from .chat_manager import ChatManager
from protocol.packet import Packet
from protocol.types import PacketFlag, MessageType, ChatType
from crypto.keys import KeyManager
from crypto.e2ee import E2EE

class MiniServer:
    def __init__(self, host='0.0.0.0', port=9000):
        self.host = host
        self.port = port
        self.storage = InMemoryStorage()
        self.chat_mgr = ChatManager(self.storage)
        self.connections = {}  # writer: user_id
    
    async def handle_client(self, reader, writer):
        user_id = f"user_{id(writer) % 10000}"
        private_key, public_key = KeyManager.generate_keypair()
        self.storage.user_keys[user_id] = {'private': private_key, 'public': public_key}
        self.storage.users[writer] = {'user_id': user_id, 'public_key': public_key}
        self.connections[writer] = user_id
        print(f"[+] {user_id} подключился")
        
        # Отправляем публичный ключ клиента (для E2EE в личных чатах)
        pkt = Packet.pack(
            PacketFlag.SYSTEM, MessageType.KEY_EX, 0, 0, 
            struct.pack('!I', len(public_key)) + public_key
        )
        writer.write(pkt)
        await writer.drain()
        
        try:
            while True:
                header = await reader.readexactly(Packet.HEADER_SIZE)
                # need to read remaining payload length; for simplicity read rest of stream
                rest = await reader.read(1024)
                flags, msg_type, chat_type, chat_id, payload = Packet.unpack(header + rest)
                
                # Обработка E2EE для личных чатов
                if flags & PacketFlag.ENCRYPTED and chat_type == ChatType.PRIVATE:
                    sender_pubkey = self._get_peer_pubkey(user_id, chat_id)  # Логика поиска ключа
                    shared_secret = KeyManager.derive_shared_secret(
                        self.storage.user_keys[user_id]['private'], 
                        sender_pubkey
                    )
                    payload = E2EE.decrypt(payload, shared_secret)
                
                # Сохраняем сообщение
                if chat_id in self.storage.chats:
                    self.storage.chats[chat_id]['messages'].append({
                        'from': user_id,
                        'data': payload,
                        'encrypted': bool(flags & PacketFlag.ENCRYPTED)
                    })
                
                # Рассылка участникам чата
                await self._broadcast(chat_id, header + payload, exclude=writer)
        except Exception as e:
            print(f"[-] {user_id} отключился: {e}")
        finally:
            self._cleanup(writer)
    
    async def _broadcast(self, chat_id: int, data: bytes, exclude=None):
        for writer, uid in self.connections.items():
            if writer != exclude and uid in self.storage.chats[chat_id]['members']:
                try:
                    writer.write(data)
                    await writer.drain()
                except: pass
    
    def _cleanup(self, writer):
        if writer in self.connections:
            uid = self.connections.pop(writer)
            del self.storage.users[writer]
            writer.close()
