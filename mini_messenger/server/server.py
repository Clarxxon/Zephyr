import asyncio
import json
import struct
import websockets
from .storage import InMemoryStorage
from .chat_manager import ChatManager
from mini_messenger.protocol.packet import Packet
from mini_messenger.protocol.types import PacketFlag, MessageType, ChatType
from mini_messenger.crypto.keys import KeyManager
from mini_messenger.crypto.e2ee import E2EE

class MiniServer:
    def __init__(self, host='0.0.0.0', port=9000, ws_port=8765):
        self.host = host
        self.port = port
        self.ws_port = ws_port
        self.storage = InMemoryStorage()
        self.chat_mgr = ChatManager(self.storage)
        self.tcp_connections = {}  # writer: user_id
        self.ws_connections = {}   # websocket: user_id
    
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
        for writer, uid in self.tcp_connections.items():
            if writer != exclude and uid in self.storage.chats[chat_id]['members']:
                try:
                    writer.write(data)
                    await writer.drain()
                except: pass

    async def _broadcast_ws(self, chat_id: int, from_user: str, text: str):
        msg = json.dumps({'chat_id': chat_id, 'from': from_user, 'text': text})
        for ws, uid in list(self.ws_connections.items()):
            if uid != from_user and uid in self.storage.chats.get(chat_id, {}).get('members', {}):
                try:
                    await ws.send(msg)
                except:
                    pass
    
    def _cleanup(self, writer):
        if writer in self.tcp_connections:
            uid = self.tcp_connections.pop(writer)
            del self.storage.users[writer]
            writer.close()

    async def websocket_handler(self, websocket):
        user_id = f"ws_{id(websocket) % 10000}"
        self.ws_connections[websocket] = user_id
        self.storage.users[websocket] = {'user_id': user_id}
        print(f"[WS+] {user_id} connected")
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                except:
                    continue
                # administrative actions
                if 'action' in data:
                    action = data['action']
                    if action == 'create':
                        chat_id = data.get('chat_id')
                        chat_type = data.get('type', ChatType.GROUP)
                        name = data.get('name')
                        if chat_id is not None:
                            self.storage.chats[chat_id] = {
                                'type': chat_type,
                                'name': name or f"Chat_{chat_id}",
                                'members': {user_id},
                                'admin': user_id if chat_type == ChatType.CHANNEL else None,
                                'messages': []
                            }
                    elif action == 'join':
                        chat_id = data.get('chat_id')
                        if chat_id in self.storage.chats:
                            self.storage.chats[chat_id]['members'].add(user_id)
                    continue
                
                # normal message
                chat_id = data.get('chat_id')
                text = data.get('text')
                if chat_id is None or text is None:
                    continue
                # create chat on the fly if not exist
                if chat_id not in self.storage.chats:
                    self.storage.chats[chat_id] = {
                        'type': ChatType.GROUP,
                        'name': f"Chat_{chat_id}",
                        'members': {user_id},
                        'admin': None,
                        'messages': []
                    }
                self.storage.chats[chat_id]['messages'].append({
                    'from': user_id,
                    'data': text.encode('utf-8'),
                    'encrypted': False
                })
                await self._broadcast_ws(chat_id, user_id, text)
        except Exception as e:
            print(f"[WS-] {user_id} disconnect: {e}")
        finally:
            self.ws_connections.pop(websocket, None)
            self.storage.users.pop(websocket, None)
            print(f"[WS-] {user_id} disconnected")

    async def start(self):
        # run both TCP and WS servers concurrently
        tcp_server = await asyncio.start_server(self.handle_client, self.host, self.port)
        ws_server = await websockets.serve(self.websocket_handler, self.host, self.ws_port)
        print(f"TCP server on {self.host}:{self.port}, WS on {self.host}:{self.ws_port}")
        async with tcp_server:
            await asyncio.gather(tcp_server.serve_forever(), ws_server.wait_closed())
