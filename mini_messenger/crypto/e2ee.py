import os
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from .keys import KeyManager

class E2EE:
    NONCE_SIZE = 12  # Оптимально для ChaCha20
    
    @staticmethod
    def encrypt(plaintext: bytes, key: bytes) -> bytes:
        """Возвращает: nonce (12) + ciphertext + tag (16)"""
        nonce = os.urandom(E2EE.NONCE_SIZE)
        chacha = ChaCha20Poly1305(key[:32])  # Используем первые 32 байта ключа
        ciphertext = chacha.encrypt(nonce, plaintext, None)
        return nonce + ciphertext  # Итого: 12 + len(plaintext) + 16
    
    @staticmethod
    def decrypt(packet: bytes, key: bytes) -> bytes:
        nonce = packet[:E2EE.NONCE_SIZE]
        ciphertext = packet[E2EE.NONCE_SIZE:]
        chacha = ChaCha20Poly1305(key[:32])
        return chacha.decrypt(nonce, ciphertext, None)
