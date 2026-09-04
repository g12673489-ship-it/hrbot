import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Парсинг списка ID администраторов
raw_admin_ids = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [
    int(x.strip().strip("'\"")) for x in raw_admin_ids.split(",") 
    if x.strip().strip("'\"").isdigit() or (x.strip().strip("'\"").startswith("-") and x.strip().strip("'\"")[1:].isdigit())
]

# ID целевой группы для откликов
raw_group_id = os.getenv("TARGET_GROUP_ID", "0").strip().strip("'\"")
try:
    TARGET_GROUP_ID = int(raw_group_id)
except ValueError:
    TARGET_GROUP_ID = 0

def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором."""
    return user_id in ADMIN_IDS
