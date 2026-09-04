from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from locales.texts import get_text

def get_main_keyboard(lang: str = "ru", is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Главное меню с поддержкой локализации."""
    buttons = [
        [KeyboardButton(text=get_text(lang, "btn_directions"))],
        [KeyboardButton(text=get_text(lang, "btn_about")), KeyboardButton(text=get_text(lang, "btn_change_lang"))]
    ]
    if is_admin:
        buttons.append([KeyboardButton(text=get_text(lang, "btn_admin"))])
        
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        persistent=True
    )

def get_cancel_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    """Клавиатура для отмены заполнения анкеты."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=get_text(lang, "btn_cancel"))]],
        resize_keyboard=True
    )

def get_skip_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой «Пропустить» и «Отмена»."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_text(lang, "btn_skip"))],
            [KeyboardButton(text=get_text(lang, "btn_cancel"))]
        ],
        resize_keyboard=True
    )

def get_confirm_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    """Клавиатура для подтверждения отправки отклика."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_text(lang, "btn_submit_app"))],
            [KeyboardButton(text=get_text(lang, "btn_cancel"))]
        ],
        resize_keyboard=True
    )

def get_contact_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    """Клавиатура для отправки контакта."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_text(lang, "btn_send_contact"), request_contact=True)],
            [KeyboardButton(text=get_text(lang, "btn_cancel"))]
        ],
        resize_keyboard=True
    )
