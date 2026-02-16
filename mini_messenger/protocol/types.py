from enum import IntEnum

class ChatType(IntEnum):
    PRIVATE = 0x01  # Личный чат (E2EE)
    GROUP   = 0x02  # Группа (серверное шифрование)
    CHANNEL = 0x03  # Канал (только отправка от админа)

class PacketFlag(IntEnum):
    COMPRESSED = 0x01
    ENCRYPTED  = 0x02
    SYSTEM     = 0x04  # Системное сообщение (вступление в группу и т.д.)

class MessageType(IntEnum):
    TEXT   = 0x01
    KEY_EX = 0x02  # Обмен ключами для E2EE
    JOIN   = 0x03  # Запрос на вступление в группу/канал
