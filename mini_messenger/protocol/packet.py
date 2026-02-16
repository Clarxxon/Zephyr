import struct
import zlib
from .types import PacketFlag

class Packet:
    HEADER_SIZE = 8  # [flags:1][msg_type:1][chat_type:1][reserved:1][chat_id:4]
    
    @staticmethod
    def pack(flags: int, msg_type: int, chat_type: int, chat_id: int, payload: bytes) -> bytes:
        if len(payload) > 0xFFFFFF:  # 16MB лимит
            raise ValueError("Payload too large")
        
        # Сжатие если нет флага ENCRYPTED (шифрование уже "сжимает" энтропию)
        if not (flags & PacketFlag.ENCRYPTED) and len(payload) > 64:
            payload = zlib.compress(payload, level=1)
            flags |= PacketFlag.COMPRESSED
        
        header = struct.pack('!BBBI', flags, msg_type, chat_type, chat_id)
        return header + payload
    
    @staticmethod
    def unpack(data: bytes) -> tuple:
        if len(data) < Packet.HEADER_SIZE:
            raise ValueError("Incomplete header")
        
        flags, msg_type, chat_type, chat_id = struct.unpack('!BBBI', data[:Packet.HEADER_SIZE])
        payload = data[Packet.HEADER_SIZE:]
        
        if flags & PacketFlag.COMPRESSED:
            payload = zlib.decompress(payload)
        
        return flags, msg_type, chat_type, chat_id, payload
