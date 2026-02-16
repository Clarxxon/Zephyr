import asyncio
import struct
from protocol.packet import Packet
from protocol.types import PacketFlag, MessageType, ChatType
from .session import Session
from crypto.e2ee import E2EE

class MiniClient:
    def __init__(self, host='127.0.0.1', port=9000):
        self.host = host
        self.port = port
        self.session = Session()
        self.reader = None
        self.writer = None
    
    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        print("✅ Подключено к серверу")
        asyncio.create_task(self._receiver())
    
    async def _receiver(self):
        while True:
            try:
                header = await self.reader.readexactly(Packet.HEADER_SIZE)
                rest = await self.reader.read(1024)
                flags, msg_type, chat_type, chat_id, payload = Packet.unpack(
                    header + rest
                )
                
                if msg_type == MessageType.KEY_EX:  # Получен публичный ключ
                    key_len = struct.unpack('!I', payload[:4])[0]
                    peer_key = payload[4:4+key_len]
                    # Логика сохранения ключа для будущих личных чатов
                    continue
                
                # Дешифрование если E2EE
                if flags & PacketFlag.ENCRYPTED and chat_id in self.session.keys:
                    payload = E2EE.decrypt(payload, self.session.keys[chat_id])
                
                text = payload.decode('utf-8', errors='replace')
                chat_name = self.session.chat_list.get(chat_id, {}).get('name', f"Chat_{chat_id}")
                print(f"\n[{chat_name}] {text}")
                print("> ", end='', flush=True)
            except Exception as e:
                print(f"\nОшибка получения: {e}")
                break
    
    async def send_message(self, chat_id: int, text: str):
        payload, is_encrypted = self.session.encrypt_for_chat(chat_id, text.encode('utf-8'))
        flags = PacketFlag.ENCRYPTED if is_encrypted else 0
        chat_type = self.session.chat_list[chat_id]['type']
        packet = Packet.pack(flags, MessageType.TEXT, chat_type, chat_id, payload)
        self.writer.write(packet)
        await self.writer.drain()
        print(f"📤 Отправлено в чат {chat_id} ({len(packet)} байт)")
