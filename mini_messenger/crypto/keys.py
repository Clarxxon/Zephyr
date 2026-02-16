from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization

class KeyManager:
    @staticmethod
    def generate_keypair():
        private = x25519.X25519PrivateKey.generate()
        public = private.public_key()
        return (
            private.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption()
            ),
            public.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
        )
    
    @staticmethod
    def derive_shared_secret(local_private: bytes, peer_public: bytes) -> bytes:
        private = x25519.X25519PrivateKey.from_private_bytes(local_private)
        public = x25519.X25519PublicKey.from_public_bytes(peer_public)
        return private.exchange(public)  # 32 байта shared secret
