from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from locales.texts import get_text

def get_language_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора языка."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang:ru"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang:en"),
                InlineKeyboardButton(text="🇺🇿 O'zbek tili", callback_data="set_lang:uz")
            ]
        ]
    )

def get_vacancies_keyboard(vacancies: list, lang: str = "ru") -> InlineKeyboardMarkup:
    """Список направлений для кандидатов."""
    buttons = []
    for vac in vacancies:
        buttons.append([
            InlineKeyboardButton(
                text=f"🚀 {vac['title']}",
                callback_data=f"user_view_vac:{vac['id']}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_vacancy_detail_keyboard(vacancy_id: int, lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура деталей направления."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text(lang, "btn_apply"),
                    callback_data=f"apply_vac:{vacancy_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_text(lang, "btn_back_directions"),
                    callback_data="back_to_vacancies"
                )
            ]
        ]
    )

def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """Главная админ-панель."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Добавить направление/команду",
                    callback_data="admin_add_vac"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Управление направлениями",
                    callback_data="admin_list_vac"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Закрыть панель",
                    callback_data="admin_close"
                )
            ]
        ]
    )

def get_admin_vacancies_keyboard(vacancies: list) -> InlineKeyboardMarkup:
    """Список всех направлений для админа."""
    buttons = []
    for vac in vacancies:
        status_icon = "🟢" if vac['is_active'] else "🔴"
        buttons.append([
            InlineKeyboardButton(
                text=f"{status_icon} {vac['title']}",
                callback_data=f"admin_view_vac:{vac['id']}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(
            text="⬅️ Назад в админ-меню",
            callback_data="admin_main_menu"
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_vacancy_detail_keyboard(vacancy_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """Управление направлением в админке."""
    toggle_text = "🔴 Скрыть направление" if is_active else "🟢 Активировать направление"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=toggle_text,
                    callback_data=f"admin_toggle_vac:{vacancy_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑️ Удалить направление",
                    callback_data=f"admin_delete_vac:{vacancy_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ К списку направлений",
                    callback_data="admin_list_vac"
                )
            ]
        ]
    )

def get_group_application_keyboard(app_id: int, user_id: int, username: str | None = None) -> InlineKeyboardMarkup:
    """Кнопки действий с заявкой студента в спец-группе."""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Принять в команду", callback_data=f"group_accept:{app_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"group_reject:{app_id}")
        ]
    ]
    if username:
        buttons.append([
            InlineKeyboardButton(text="💬 Написать кандидату", url=f"https://t.me/{username}")
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
