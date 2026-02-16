import os
import json


class RedisCache:
    """Простой распределённый кэш на базе Redis.

    Используется для хранения метаданных чатов (тип, имя, участники) и
    очереди сообщений. Клиенты могут запускаться на нескольких серверах,
    разделяющих Redis, что даёт базовую поддержку распределённости.
    """

    def __init__(self, url: str | None = None):
        try:
            import redis
        except ImportError:
            raise RuntimeError("redis package is required for RedisCache")

        self.url = url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        # decode_responses=True позволяет работать со строками вместо байтов
        self.r = redis.from_url(self.url, decode_responses=True)

    def store_chat(self, chat_id: int, chat_obj: dict):
        # подготовим объект, конвертируя множество в список
        obj = {**chat_obj}
        if "members" in obj and isinstance(obj["members"], (set, list)):
            obj["members"] = list(obj["members"])
        # не сохраняем сообщения в основном хэше, они хранятся в списке
        obj.pop("messages", None)
        self.r.hset("chats", chat_id, json.dumps(obj))
        # хранение множества участников отдельно для быстрого доступа
        if "members" in chat_obj:
            key = f"chat:{chat_id}:members"
            # перезаписать целиком
            self.r.delete(key)
            if chat_obj["members"]:
                self.r.sadd(key, *chat_obj["members"])

    def get_chat(self, chat_id: int) -> dict | None:
        val = self.r.hget("chats", chat_id)
        if not val:
            return None
        obj = json.loads(val)
        if "members" in obj:
            obj["members"] = set(obj["members"])
        # добавим сообщения из списка, если нужно
        return obj

    def add_member(self, chat_id: int, user_id: str):
        key = f"chat:{chat_id}:members"
        self.r.sadd(key, user_id)
        # синхронизируем основной хэш
        chat = self.get_chat(chat_id)
        if chat:
            chat_members = chat.get("members", set())
            chat_members.add(user_id)
            chat["members"] = chat_members
            self.store_chat(chat_id, chat)

    def get_members(self, chat_id: int) -> set:
        return set(self.r.smembers(f"chat:{chat_id}:members"))

    def add_message(self, chat_id: int, message_obj: dict):
        key = f"chat:{chat_id}:messages"
        self.r.rpush(key, json.dumps(message_obj))

    def get_messages(self, chat_id: int) -> list:
        key = f"chat:{chat_id}:messages"
        raw = self.r.lrange(key, 0, -1)
        return [json.loads(m) for m in raw]
