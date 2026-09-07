import re
import logging

logger = logging.getLogger(__name__)

def escape_md(text: str) -> str:
    """Экранирование спецсимволов Telegram Markdown v1."""
    if not text:
        return text
    for ch in ('_', '*', '`', '['):
        text = text.replace(ch, '\\' + ch)
    return text
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from config import is_admin, TARGET_GROUP_ID
from database.db import (
    get_active_vacancies,
    get_vacancy_by_id,
    create_application,
    has_recent_application,
    get_user_lang,
    set_user_lang
)
from locales.texts import get_text
from states.application import ApplicationForm
from keyboards.reply import (
    get_main_keyboard,
    get_cancel_keyboard,
    get_skip_keyboard,
    get_confirm_keyboard,
    get_contact_keyboard
)
from keyboards.inline import (
    get_language_keyboard,
    get_vacancies_keyboard,
    get_vacancy_detail_keyboard,
    get_group_application_keyboard
)

router = Router()

async def send_main_menu(message_or_bot, user_id: int, chat_id: int = None):
    """Утилита для отправки главного меню с reply-клавиатурой."""
    user_lang = await get_user_lang(user_id)
    user_is_admin = is_admin(user_id)
    kb = get_main_keyboard(user_lang, is_admin=user_is_admin)
    
    if isinstance(message_or_bot, Message):
        await message_or_bot.answer("👇", reply_markup=kb)
    elif isinstance(message_or_bot, Bot) and chat_id:
        await message_or_bot.send_message(chat_id=chat_id, text="👇", reply_markup=kb)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    user_lang = await get_user_lang(user_id)
    user_is_admin = is_admin(user_id)
    
    # Приветствие
    welcome_text = get_text(user_lang, "welcome", name=message.from_user.full_name)
    await message.answer(
        welcome_text,
        reply_markup=get_main_keyboard(user_lang, is_admin=user_is_admin),
        parse_mode="Markdown"
    )

# --- ВЫБОР И СМЕНА ЯЗЫКА ---

@router.message(F.text.in_(["🌐 Язык / Language / Til", "🌐 Language / Язык / Til", "🌐 Til / Language / Язык"]))
async def cmd_change_lang(message: Message):
    user_lang = await get_user_lang(message.from_user.id)
    await message.answer(
        get_text(user_lang, "select_lang"),
        reply_markup=get_language_keyboard()
    )

@router.callback_query(F.data.startswith("set_lang:"))
async def cb_set_lang(callback: CallbackQuery):
    lang_code = callback.data.split(":")[1]
    user_id = callback.from_user.id
    await set_user_lang(user_id, lang_code)
    
    user_is_admin = is_admin(user_id)
    confirm_text = get_text(lang_code, "lang_saved")
    
    # Удаляем inline-клавиатуру выбора языка
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    # Отправляем подтверждение + главное меню на новом языке
    await callback.message.answer(
        confirm_text,
        reply_markup=get_main_keyboard(lang_code, is_admin=user_is_admin)
    )
    await callback.answer()

# --- ОТМЕНА ДЕЙСТВИЯ ---

@router.message(F.text.in_(["❌ Отмена", "❌ Cancel", "❌ Bekor qilish"]))
async def cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    user_lang = await get_user_lang(message.from_user.id)
    user_is_admin = is_admin(message.from_user.id)
    await message.answer(
        get_text(user_lang, "cancel_action"),
        reply_markup=get_main_keyboard(user_lang, is_admin=user_is_admin)
    )

# --- ИНФОРМАЦИЯ О КОМАНДАХ ---

@router.message(F.text.in_(["ℹ️ О наших командах", "ℹ️ About Our Team", "ℹ️ Jamoamiz haqida"]))
async def cmd_about(message: Message):
    user_lang = await get_user_lang(message.from_user.id)
    await message.answer(
        get_text(user_lang, "about_text"),
        parse_mode="Markdown"
    )

# --- ПРОСМОТР НАПРАВЛЕНИЙ ---

@router.message(F.text.in_(["🚀 Команды и направления", "🚀 Teams & Directions", "🚀 Jamoalar va yo'nalishlar"]))
async def show_vacancies_command(message: Message):
    user_lang = await get_user_lang(message.from_user.id)
    vacancies = await get_active_vacancies()
    
    if not vacancies:
        await message.answer(get_text(user_lang, "no_directions"))
        return

    await message.answer(
        get_text(user_lang, "select_direction"),
        reply_markup=get_vacancies_keyboard(vacancies, user_lang),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "back_to_vacancies")
async def cb_back_to_vacancies(callback: CallbackQuery):
    user_lang = await get_user_lang(callback.from_user.id)
    vacancies = await get_active_vacancies()
    
    if not vacancies:
        await callback.message.edit_text(get_text(user_lang, "no_directions"))
        await callback.answer()
        return

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        get_text(user_lang, "select_direction"),
        reply_markup=get_vacancies_keyboard(vacancies, user_lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("user_view_vac:"))
async def user_view_vacancy(callback: CallbackQuery):
    user_lang = await get_user_lang(callback.from_user.id)
    vac_id = int(callback.data.split(":")[1])
    vac = await get_vacancy_by_id(vac_id)
    
    if not vac or not vac["is_active"]:
        await callback.answer(get_text(user_lang, "direction_unavailable"), show_alert=True)
        return

    text = (
        f"🚀 **{vac['title']}**\n\n"
        f"📝 **Описание направления:**\n{vac['description']}\n\n"
        f"🎯 **Кого мы ищем / Требования:**\n{vac['requirements']}"
    )

    try:
        await callback.message.delete()
    except Exception:
        pass

    if vac.get('photo_id'):
        if len(text) <= 1000:
            await callback.message.answer_photo(
                photo=vac['photo_id'],
                caption=text,
                reply_markup=get_vacancy_detail_keyboard(vac_id, user_lang),
                parse_mode="Markdown"
            )
        else:
            await callback.message.answer_photo(photo=vac['photo_id'])
            await callback.message.answer(
                text,
                reply_markup=get_vacancy_detail_keyboard(vac_id, user_lang),
                parse_mode="Markdown"
            )
    else:
        await callback.message.answer(
            text,
            reply_markup=get_vacancy_detail_keyboard(vac_id, user_lang),
            parse_mode="Markdown"
        )
    await callback.answer()

# --- ПОДАЧА АНКЕТЫ СТУДЕНТА (FSM) ---

@router.callback_query(F.data.startswith("apply_vac:"))
async def start_application(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_lang = await get_user_lang(user_id)
    user_is_admin = is_admin(user_id)
    vac_id = int(callback.data.split(":")[1])
    vac = await get_vacancy_by_id(vac_id)
    
    if not vac or not vac["is_active"]:
        await callback.answer(get_text(user_lang, "direction_unavailable"), show_alert=True)
        return

    # Проверка лимита 24 часов на повторную подачу заявки
    has_recent, remaining_seconds = await has_recent_application(user_id, vac_id, hours=24)
    if has_recent and not user_is_admin:
        hours = remaining_seconds // 3600
        minutes = (remaining_seconds % 3600) // 60
        
        cooldown_text = get_text(
            user_lang, "cooldown_msg",
            title=vac["title"],
            hours=hours,
            minutes=minutes
        )
        
        await callback.message.answer(
            cooldown_text,
            reply_markup=get_main_keyboard(user_lang, is_admin=user_is_admin),
            parse_mode="Markdown"
        )
        await callback.answer()
        return

    await state.set_state(ApplicationForm.full_name)
    await state.update_data(vacancy_id=vac_id, vacancy_title=vac["title"], lang=user_lang)

    start_text = (
        f"🎯 **Выбранная роль / направление:**\n"
        f"👉 **{vac['title']}**\n\n"
        f"{get_text(user_lang, 'step_name')}"
    )

    await callback.message.answer(
        start_text,
        reply_markup=get_cancel_keyboard(user_lang),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(ApplicationForm.full_name, ~F.text.startswith("❌"))
async def process_app_name(message: Message, state: FSMContext):
    user_lang = await get_user_lang(message.from_user.id)
    text = message.text.strip()
    
    # Валидация имени: только буквы, минимум 2 слова, длина от 3 до 50
    if len(text.split()) < 2 or not re.match(r"^[A-Za-zА-Яа-яЎўҚқҒғҲҳ\-\s]{3,50}$", text):
        await message.answer(get_text(user_lang, "err_name"))
        return
        
    await state.update_data(full_name=text)
    await state.set_state(ApplicationForm.course)
    
    await message.answer(
        get_text(user_lang, "step_course"),
        reply_markup=get_cancel_keyboard(user_lang),
        parse_mode="Markdown"
    )

@router.message(ApplicationForm.course, ~F.text.startswith("❌"))
async def process_app_course(message: Message, state: FSMContext):
    user_lang = await get_user_lang(message.from_user.id)
    await state.update_data(course=message.text.strip())
    await state.set_state(ApplicationForm.student_id)
    
    await message.answer(
        get_text(user_lang, "step_student_id"),
        reply_markup=get_cancel_keyboard(user_lang),
        parse_mode="Markdown"
    )

@router.message(ApplicationForm.student_id, ~F.text.startswith("❌"))
async def process_app_student_id(message: Message, state: FSMContext):
    user_lang = await get_user_lang(message.from_user.id)
    text = message.text.strip()
    
    # Валидация Student ID: буквы в начале, затем цифры (например su12345, ad123821)
    clean_text = text.replace(" ", "")
    if not re.match(r"^[A-Za-z]{2,5}\d{4,10}$", clean_text):
        await message.answer(get_text(user_lang, "err_student_id"))
        return
        
    await state.update_data(student_id=clean_text)
    await state.set_state(ApplicationForm.contact_info)
    
    await message.answer(
        get_text(user_lang, "step_phone"),
        reply_markup=get_contact_keyboard(user_lang),
        parse_mode="Markdown"
    )

@router.message(ApplicationForm.contact_info)
async def process_app_contact(message: Message, state: FSMContext):
    if message.text and message.text.startswith("❌"):
        return await cancel_handler(message, state)
        
    user_lang = await get_user_lang(message.from_user.id)
    if message.contact:
        phone = message.contact.phone_number
    elif message.text:
        phone = message.text.strip()
    else:
        return
        
    await state.update_data(contact_info=phone)
    await state.set_state(ApplicationForm.cv_portfolio)
    
    await message.answer(
        get_text(user_lang, "step_cv"),
        reply_markup=get_skip_keyboard(user_lang),
        parse_mode="Markdown"
    )

@router.message(ApplicationForm.cv_portfolio, ~F.text.startswith("❌"))
async def process_app_cv(message: Message, state: FSMContext):
    user_lang = await get_user_lang(message.from_user.id)
    text = message.text.strip()
    
    if text in ["⏩ Пропустить", "⏩ Skip", "⏩ O'tkazib yuborish"]:
        cv_text = "—"
    else:
        cv_text = text
        
    await state.update_data(cv_portfolio=cv_text)
    await state.set_state(ApplicationForm.motivation)
    
    await message.answer(
        get_text(user_lang, "step_motivation"),
        reply_markup=get_cancel_keyboard(user_lang),
        parse_mode="Markdown"
    )

@router.message(ApplicationForm.motivation, ~F.text.startswith("❌"))
async def process_app_motivation(message: Message, state: FSMContext):
    user_lang = await get_user_lang(message.from_user.id)
    text = message.text.strip()
    
    if len(text) < 15:
        await message.answer(get_text(user_lang, "err_motivation"))
        return
        
    await state.update_data(motivation=text)
    await state.set_state(ApplicationForm.confirm)
    
    data = await state.get_data()
    
    preview_text = (
        get_text(user_lang, "preview_title") +
        get_text(user_lang, "preview_direction", title=data["vacancy_title"]) +
        get_text(user_lang, "preview_name", name=data["full_name"]) +
        get_text(user_lang, "preview_course", course=data["course"]) +
        get_text(user_lang, "preview_student_id", student_id=data["student_id"]) +
        get_text(user_lang, "preview_phone", phone=data["contact_info"]) +
        get_text(user_lang, "preview_cv", cv=data["cv_portfolio"]) +
        get_text(user_lang, "preview_motivation", motivation=data["motivation"]) +
        get_text(user_lang, "preview_confirm")
    )
    
    await message.answer(
        preview_text,
        reply_markup=get_confirm_keyboard(user_lang),
        parse_mode="Markdown"
    )

@router.message(ApplicationForm.confirm, F.text.in_(["✅ Отправить заявку", "✅ Submit Application", "✅ Ariza yuborish"]))
async def submit_application(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user = message.from_user
    user_lang = data.get("lang", "ru")
    user_is_admin = is_admin(user.id)
    
    # 1. Сохраняем заявку в БД
    app_id = await create_application(
        vacancy_id=data["vacancy_id"],
        vacancy_title=data["vacancy_title"],
        user_id=user.id,
        full_name=data["full_name"],
        course=data["course"],
        student_id=data["student_id"],
        username=user.username,
        contact_info=data["contact_info"],
        cv_portfolio=data["cv_portfolio"],
        motivation=data["motivation"],
        lang=user_lang
    )
    
    await state.clear()
    
    # 2. Подтверждение + возврат в главное меню
    await message.answer(
        get_text(user_lang, "app_success"),
        reply_markup=get_main_keyboard(user_lang, is_admin=user_is_admin),
        parse_mode="Markdown"
    )
    
    # 3. Карточка студента в спец-группу HR/Руководителям
    logger.info(f"Отправка заявки #{app_id} в группу TARGET_GROUP_ID={TARGET_GROUP_ID}")
    if TARGET_GROUP_ID and TARGET_GROUP_ID != 0:
        username_str = f"@{user.username}" if user.username else "Отсутствует"
        
        # Экранируем пользовательские данные, чтобы спецсимволы не ломали Markdown
        safe_name = escape_md(data['full_name'])
        safe_course = escape_md(data['course'])
        safe_cv = escape_md(data['cv_portfolio'])
        safe_motivation = escape_md(data['motivation'])
        safe_title = escape_md(data['vacancy_title'])
        safe_contact = escape_md(data['contact_info'])
        
        group_card_text = (
            f"🎯 *НА КАКУЮ РОЛЬ ПОДАЕТСЯ КАНДИДАТ:*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔥 *{safe_title}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📋 *ДАННЫЕ КАНДИДАТА:*\n"
            f"👤 *ФИО:* {safe_name}\n"
            f"🎓 *Курс:* {safe_course}\n"
            f"🪪 *Student ID:* `{data['student_id']}`\n"
            f"✈️ *Telegram:* {username_str} (ID: `{user.id}`)\n"
            f"📞 *Контакты:* {safe_contact}\n"
            f"📄 *CV / Портфолио:* {safe_cv}\n"
            f"🌐 *Язык анкеты:* {user_lang.upper()}\n\n"
            f"🧠 *Мотивация / Почему хочет в команду:*\n{safe_motivation}\n\n"
            f"🔖 _Анкета №{app_id}_"
        )
        
        sent = False
        target_id = TARGET_GROUP_ID
        
        # Попытка 1: отправка с Markdown
        try:
            await bot.send_message(
                chat_id=target_id,
                text=group_card_text,
                reply_markup=get_group_application_keyboard(app_id, user.id, user.username),
                parse_mode="Markdown"
            )
            sent = True
            logger.info(f"Заявка #{app_id} успешно отправлена в группу {target_id}")
        except Exception as e:
            logger.error(f"Ошибка отправки заявки #{app_id} в группу ({target_id}): {e}", exc_info=True)
            
            # Проверка миграции чата
            new_chat_id = getattr(e, "migrate_to_chat_id", None)
            if not new_chat_id and "migrated to a supergroup with id" in str(e).lower():
                try:
                    new_chat_id = int(str(e).split("migrated to a supergroup with id ")[1].split()[0])
                except Exception:
                    pass
            
            if new_chat_id:
                target_id = new_chat_id
                logger.info(f"Группа мигрировала, новый ID: {new_chat_id}")
                try:
                    await bot.send_message(
                        chat_id=new_chat_id,
                        text=group_card_text,
                        reply_markup=get_group_application_keyboard(app_id, user.id, user.username),
                        parse_mode="Markdown"
                    )
                    sent = True
                    logger.info(f"Сообщение отправлено в мигрированную супергруппу {new_chat_id}")
                except Exception as e2:
                    logger.error(f"Ошибка отправки в мигрированную супергруппу ({new_chat_id}): {e2}", exc_info=True)
        
        # Попытка 2 (fallback): если Markdown не сработал, отправляем без форматирования
        if not sent:
            logger.warning(f"Fallback: отправка заявки #{app_id} без parse_mode в {target_id}")
            plain_text = (
                f"🎯 НА КАКУЮ РОЛЬ ПОДАЕТСЯ КАНДИДАТ:\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔥 {data['vacancy_title']}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📋 ДАННЫЕ КАНДИДАТА:\n"
                f"👤 ФИО: {data['full_name']}\n"
                f"🎓 Курс: {data['course']}\n"
                f"🪪 Student ID: {data['student_id']}\n"
                f"✈️ Telegram: {username_str} (ID: {user.id})\n"
                f"📞 Контакты: {data['contact_info']}\n"
                f"📄 CV / Портфолио: {data['cv_portfolio']}\n"
                f"🌐 Язык анкеты: {user_lang.upper()}\n\n"
                f"🧠 Мотивация / Почему хочет в команду:\n{data['motivation']}\n\n"
                f"🔖 Анкета №{app_id}"
            )
            try:
                await bot.send_message(
                    chat_id=target_id,
                    text=plain_text,
                    reply_markup=get_group_application_keyboard(app_id, user.id, user.username)
                )
                logger.info(f"Заявка #{app_id} отправлена в группу {target_id} (без Markdown)")
            except Exception as e3:
                logger.error(f"КРИТИЧЕСКАЯ ОШИБКА: не удалось отправить заявку #{app_id} в группу ({target_id}) даже без Markdown: {e3}", exc_info=True)
    else:
        logger.warning(f"TARGET_GROUP_ID не задан или равен 0! Заявка #{app_id} НЕ отправлена в группу.")


