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
                sent_to_group INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vacancy_id) REFERENCES vacancies (id) ON DELETE CASCADE
            );
        """)

        # Таблица посещений (для статистики)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        await db.commit()

        # --- Миграции (безопасное добавление колонок) ---
        migrations = [
            "ALTER TABLE vacancies ADD COLUMN photo_id TEXT DEFAULT NULL;",
            "ALTER TABLE applications ADD COLUMN sent_to_group INTEGER DEFAULT 0;",
        ]
        for sql in migrations:
            try:
                await db.execute(sql)
                await db.commit()
            except Exception:
                pass  # Колонка уже существует

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

# --- ПОСЕЩЕНИЯ ---

async def log_visit(user_id: int):
    """Записать посещение пользователя (команда /start)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO user_visits (user_id) VALUES (?)", (user_id,)
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
            (vacancy_id, vacancy_title, user_id, full_name, course, student_id, username, contact_info, cv_portfolio, motivation, lang, sent_to_group)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                vacancy_id, vacancy_title, user_id, full_name, course, student_id,
                username, contact_info, cv_portfolio, motivation, lang
            )
        )
        await db.commit()
        return cursor.lastrowid

async def mark_application_sent(app_id: int):
    """Отметить заявку как успешно отправленную в группу."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE applications SET sent_to_group = 1 WHERE id = ?", (app_id,)
        )
        await db.commit()

async def get_unsent_applications() -> list:
    """Получить все заявки, которые НЕ были отправлены в группу."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM applications 
            WHERE sent_to_group = 0 
            ORDER BY id ASC
            """
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

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

# --- СТАТИСТИКА ---

async def get_stats() -> dict:
    """
    Получить статистику бота:
    - посещения за сегодня / вчера / неделю
    - заявки за сегодня / вчера / неделю
    - всего заявок
    - не отправленных в группу
    """
    async with aiosqlite.connect(DB_PATH) as db:
        stats = {}

        # --- Посещения ---
        visit_queries = {
            "visits_today": "date(visited_at) = date('now', 'localtime')",
            "visits_yesterday": "date(visited_at) = date('now', '-1 day', 'localtime')",
            "visits_week": "visited_at >= datetime('now', '-7 days', 'localtime')",
        }
        for key, condition in visit_queries.items():
            async with db.execute(
                f"SELECT COUNT(*) FROM user_visits WHERE {condition}"
            ) as cur:
                row = await cur.fetchone()
                stats[key] = row[0] if row else 0

        # --- Уникальные посетители ---
        async with db.execute(
            "SELECT COUNT(DISTINCT user_id) FROM user_visits WHERE visited_at >= datetime('now', '-7 days', 'localtime')"
        ) as cur:
            row = await cur.fetchone()
            stats["unique_users_week"] = row[0] if row else 0

        # --- Заявки ---
        app_queries = {
            "apps_today": "date(created_at) = date('now', 'localtime')",
            "apps_yesterday": "date(created_at) = date('now', '-1 day', 'localtime')",
            "apps_week": "created_at >= datetime('now', '-7 days', 'localtime')",
            "apps_total": "1=1",
        }
        for key, condition in app_queries.items():
            async with db.execute(
                f"SELECT COUNT(*) FROM applications WHERE {condition}"
            ) as cur:
                row = await cur.fetchone()
                stats[key] = row[0] if row else 0

        # --- Не отправленные в группу ---
        async with db.execute(
            "SELECT COUNT(*) FROM applications WHERE sent_to_group = 0"
        ) as cur:
            row = await cur.fetchone()
            stats["unsent_count"] = row[0] if row else 0

        return stats
