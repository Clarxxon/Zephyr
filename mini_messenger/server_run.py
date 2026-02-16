import asyncio
from mini_messenger.server.server import MiniServer

if __name__ == "__main__":
    server = MiniServer()
    print("🚀 Сервер запущен. Поддержка: личные чаты (E2EE), группы, каналы")
    asyncio.run(server.start())
