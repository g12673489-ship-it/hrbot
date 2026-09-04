import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "hr_bot.db")

async def init_db():
    """Инициализация базы данных и создание таблиц."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        
        # Таблица языков пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_languages (
                user_id INTEGER PRIMARY KEY,
                lang TEXT DEFAULT 'en'
            );
        """)
        
        # Таблица команд и направлений (vacancies)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS vacancies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                requirements TEXT NOT NULL,
                salary TEXT DEFAULT '',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                photo_id TEXT DEFAULT NULL
            );
        """)
        
        # Миграция: добавляем photo_id, если его нет
        try:
            await db.execute("ALTER TABLE vacancies ADD COLUMN photo_id TEXT DEFAULT NULL;")
        except Exception:
            pass # Колонка уже существует
            
        # Таблица откликов студентов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vacancy_id INTEGER NOT NULL,
                vacancy_title TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                full_name TEXT NOT NULL,
                course TEXT DEFAULT '',
                student_id TEXT DEFAULT '',
                username TEXT,
                contact_info TEXT NOT NULL,
                cv_portfolio TEXT DEFAULT '',
                motivation TEXT DEFAULT '',
                lang TEXT DEFAULT 'en',
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vacancy_id) REFERENCES vacancies (id) ON DELETE CASCADE
            );
        """)
        await db.commit()

# --- ЯЗЫКИ ПОЛЬЗОВАТЕЛЕЙ ---

async def get_user_lang(user_id: int) -> str:
    """Получить сохраненный язык пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT lang FROM user_languages WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else "en"

async def set_user_lang(user_id: int, lang: str):
    """Сохранить или обновить язык пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO user_languages (user_id, lang) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET lang = excluded.lang
            """,
            (user_id, lang)
        )
        await db.commit()

# --- НАПРАВЛЕНИЯ / КОМАНДЫ ---

async def create_vacancy(title: str, description: str, requirements: str, photo_id: str | None = None) -> int:
    """Создать новое направление/команду."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO vacancies (title, description, requirements, salary, photo_id)
            VALUES (?, ?, ?, '', ?)
            """,
            (title, description, requirements, photo_id)
        )
        await db.commit()
        return cursor.lastrowid

async def get_active_vacancies():
    """Получить список всех активных направлений."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM vacancies WHERE is_active = 1 ORDER BY id DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_all_vacancies():
    """Получить список всех направлений (для админа)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM vacancies ORDER BY id DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_vacancy_by_id(vacancy_id: int):
    """Получить направление по ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM vacancies WHERE id = ?", (vacancy_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def toggle_vacancy_active(vacancy_id: int) -> bool:
    """Переключить статус активности направления (активна/скрыта)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT is_active FROM vacancies WHERE id = ?", (vacancy_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return False
            new_status = 0 if row[0] == 1 else 1
            
        await db.execute(
            "UPDATE vacancies SET is_active = ? WHERE id = ?", (new_status, vacancy_id)
        )
        await db.commit()
        return bool(new_status)

async def delete_vacancy(vacancy_id: int):
    """Удалить направление."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM vacancies WHERE id = ?", (vacancy_id,))
        await db.commit()

# --- ОТКЛИКИ / ЗАЯВКИ СТУДЕНТОВ ---

async def create_application(
    vacancy_id: int,
    vacancy_title: str,
    user_id: int,
    full_name: str,
    course: str,
    student_id: str,
    username: str | None,
    contact_info: str,
    cv_portfolio: str,
    motivation: str,
    lang: str = "en"
) -> int:
    """Сохранить новую заявку студента."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO applications 
            (vacancy_id, vacancy_title, user_id, full_name, course, student_id, username, contact_info, cv_portfolio, motivation, lang)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                vacancy_id, vacancy_title, user_id, full_name, course, student_id,
                username, contact_info, cv_portfolio, motivation, lang
            )
        )
        await db.commit()
        return cursor.lastrowid

async def has_recent_application(user_id: int, vacancy_id: int, hours: int = 24) -> tuple[bool, int]:
    """
    Проверяет, подавал ли пользователь заявку на эту же вакансию за последние `hours` часов.
    Возвращает (has_recent: bool, remaining_seconds: int).
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT (strftime('%s', 'now') - strftime('%s', created_at)) AS diff_seconds
            FROM applications 
            WHERE user_id = ? AND vacancy_id = ? 
            ORDER BY id DESC LIMIT 1
            """,
            (user_id, vacancy_id)
        ) as cursor:
            row = await cursor.fetchone()
            if row and row[0] is not None:
                diff_seconds = int(row[0])
                cooldown_seconds = hours * 3600
                if diff_seconds < cooldown_seconds:
                    remaining_seconds = cooldown_seconds - diff_seconds
                    return True, remaining_seconds
            return False, 0

async def get_application_by_id(app_id: int):
    """Получить заявку по ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM applications WHERE id = ?", (app_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def update_application_status(app_id: int, status: str):
    """Обновить статус заявки ('accepted', 'rejected', 'pending')."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE applications SET status = ? WHERE id = ?", (status, app_id)
        )
        await db.commit()
