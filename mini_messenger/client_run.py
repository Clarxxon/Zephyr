import asyncio
from client.client import MiniClient

async def main():
    client = MiniClient()
    await client.connect()
    
    # Пример: создание личного чата (в реальном клиенте — через меню)
    # client.session.init_e2ee(chat_id, peer_pubkey)
    
    print("Команды: /chat <id> — выбрать чат, /msg <text> — отправить")
    current_chat = None
    
    while True:
        cmd = await asyncio.get_event_loop().run_in_executor(None, input, "> ")
        if cmd.startswith("/chat "):
            current_chat = int(cmd.split()[1])
            print(f"Текущий чат: {current_chat}")
        elif cmd.startswith("/msg ") and current_chat:
            await client.send_message(current_chat, cmd[5:])
        elif cmd == "exit":
            break

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nВыход")
