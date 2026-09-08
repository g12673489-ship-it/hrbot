import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)

from config import is_admin, TARGET_GROUP_ID
from database.db import (
    create_vacancy,
    get_all_vacancies,
    get_vacancy_by_id,
    toggle_vacancy_active,
    delete_vacancy,
    get_user_lang,
    get_stats,
    get_unsent_applications,
    mark_application_sent
)
from states.vacancy import VacancyForm
from keyboards.reply import get_main_keyboard, get_cancel_keyboard
from keyboards.inline import (
    get_admin_main_keyboard,
    get_admin_vacancies_keyboard,
    get_admin_vacancy_detail_keyboard
)

router = Router()

def check_admin_permission(user_id: int) -> bool:
    return is_admin(user_id)

@router.message(Command("admin"))
@router.message(F.text.in_(["⚙️ Админ-панель", "⚙️ Admin Panel", "⚙️ Admin panel"]))
async def cmd_admin(message: Message, state: FSMContext):
    if not check_admin_permission(message.from_user.id):
        await message.answer("❌ У вас нет доступа к административной панели.")
        return
    
    await state.clear()
    await message.answer(
        "⚙️ **Административная панель управления командами**\n\n"
        "Выберите нужное действие:",
        reply_markup=get_admin_main_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin_main_menu")
async def cb_admin_main_menu(callback: CallbackQuery, state: FSMContext):
    if not check_admin_permission(callback.from_user.id):
        await callback.answer("У вас нет прав.", show_alert=True)
        return
        
    await state.clear()
    await callback.message.edit_text(
        "⚙️ **Административная панель управления командами**\n\n"
        "Выберите нужное действие:",
        reply_markup=get_admin_main_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "admin_close")
async def cb_admin_close(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()

# --- ДОБАВЛЕНИЕ НАПРАВЛЕНИЯ / КОМАНДЫ (FSM) ---

@router.callback_query(F.data == "admin_add_vac")
async def start_add_vacancy(callback: CallbackQuery, state: FSMContext):
    if not check_admin_permission(callback.from_user.id):
        await callback.answer("У вас нет прав.", show_alert=True)
        return
        
    user_lang = await get_user_lang(callback.from_user.id)
    await state.set_state(VacancyForm.title)
    await callback.message.answer(
        "➕ **Шаг 1 из 3: Название направления / команды**\n\n"
        "Введите название (например: *Drone Soccer*, *Formula Student*, *Software Startup*):",
        reply_markup=get_cancel_keyboard(user_lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(VacancyForm.title, ~F.text.startswith("❌"))
async def process_title(message: Message, state: FSMContext):
    user_lang = await get_user_lang(message.from_user.id)
    await state.update_data(title=message.text.strip())
    await state.set_state(VacancyForm.description)
    await message.answer(
        "📝 **Шаг 2 из 3: Описание направления**\n\n"
        "Опишите проект, цели команды и сферу деятельности:",
        reply_markup=get_cancel_keyboard(user_lang),
        parse_mode="Markdown"
    )

@router.message(VacancyForm.description, ~F.text.startswith("❌"))
async def process_description(message: Message, state: FSMContext):
    user_lang = await get_user_lang(message.from_user.id)
    await state.update_data(description=message.text.strip())
    await state.set_state(VacancyForm.requirements)
    await message.answer(
        "🎯 **Шаг 3 из 3: Требования и разыскиваемые роли**\n\n"
        "Укажите кого вы ищете (например: *3D-моделлеры, пилоты, программисты C++/Python*):",
        reply_markup=get_cancel_keyboard(user_lang),
        parse_mode="Markdown"
    )

@router.message(VacancyForm.requirements, ~F.text.startswith("❌"))
async def process_requirements(message: Message, state: FSMContext):
    user_lang = await get_user_lang(message.from_user.id)
    await state.update_data(requirements=message.text.strip())
    await state.set_state(VacancyForm.photo)
    
    # Импортируем get_skip_keyboard локально или из keyboards.reply
    from keyboards.reply import get_skip_keyboard
    
    await message.answer(
        "🖼 **Шаг 4 из 4: Фото направления (Необязательно)**\n\n"
        "Отправьте картинку (фото), которая будет отображаться кандидатам при просмотре.\n"
        "Если фото не нужно, нажмите **«⏩ Пропустить»**.",
        reply_markup=get_skip_keyboard("ru"),
        parse_mode="Markdown"
    )

@router.message(VacancyForm.photo, ~F.text.startswith("❌"))
async def process_photo(message: Message, state: FSMContext):
    user_lang = await get_user_lang(message.from_user.id)
    
    photo_id = None
    if message.photo:
        photo_id = message.photo[-1].file_id
    elif message.text and message.text.strip() not in ["⏩ Пропустить", "⏩ Skip", "⏩ O'tkazib yuborish"]:
        # Если отправили текст, но это не кнопка пропуска
        await message.answer("Пожалуйста, отправьте фото или нажмите «Пропустить».")
        return
        
    data = await state.get_data()
    
    vac_id = await create_vacancy(
        title=data["title"],
        description=data["description"],
        requirements=data["requirements"],
        photo_id=photo_id
    )
    
    await state.clear()
    
    await message.answer(
        f"✅ **Направление успешно создано!** (ID: {vac_id})\n\n"
        f"🚀 **Команда:** {data['title']}",
        reply_markup=get_main_keyboard(user_lang, is_admin=True),
        parse_mode="Markdown"
    )

# --- СПИСОК И УПРАВЛЕНИЕ НАПРАВЛЕНИЯМИ ---

@router.callback_query(F.data == "admin_list_vac")
async def list_vacancies_admin(callback: CallbackQuery):
    if not check_admin_permission(callback.from_user.id):
        await callback.answer("У вас нет прав.", show_alert=True)
        return
        
    vacancies = await get_all_vacancies()
    if not vacancies:
        await callback.message.edit_text(
            "📋 **Список направлений пуст.**\n\nНажмите ниже, чтобы добавить новое направление:",
            reply_markup=get_admin_main_keyboard(),
            parse_mode="Markdown"
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "📋 **Список всех направлений и команд:**\n"
        "🟢 — Набор открыт\n"
        "🔴 — Набор скрыт\n\n"
        "Выберите направление для редактирования:",
        reply_markup=get_admin_vacancies_keyboard(vacancies),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_view_vac:"))
async def view_vacancy_admin(callback: CallbackQuery):
    if not check_admin_permission(callback.from_user.id):
        await callback.answer("У вас нет прав.", show_alert=True)
        return
        
    vac_id = int(callback.data.split(":")[1])
    vac = await get_vacancy_by_id(vac_id)
    if not vac:
        await callback.answer("Направление не найдено.", show_alert=True)
        return

    status_str = "🟢 Активно (Набор открыт)" if vac["is_active"] else "🔴 Скрыто"
    text = (
        f"🚀 **{vac['title']}** ({status_str})\n\n"
        f"📝 **Описание:**\n{vac['description']}\n\n"
        f"🎯 **Требования / Кто нужен:**\n{vac['requirements']}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_admin_vacancy_detail_keyboard(vac["id"], bool(vac["is_active"])),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_toggle_vac:"))
async def toggle_vacancy_admin(callback: CallbackQuery):
    if not check_admin_permission(callback.from_user.id):
        await callback.answer("У вас нет прав.", show_alert=True)
        return
        
    vac_id = int(callback.data.split(":")[1])
    new_status = await toggle_vacancy_active(vac_id)
    
    vac = await get_vacancy_by_id(vac_id)
    status_str = "🟢 Активно" if new_status else "🔴 Скрыто"
    
    text = (
        f"🚀 **{vac['title']}** ({status_str})\n\n"
        f"📝 **Описание:**\n{vac['description']}\n\n"
        f"🎯 **Требования / Кто нужен:**\n{vac['requirements']}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_admin_vacancy_detail_keyboard(vac["id"], new_status),
        parse_mode="Markdown"
    )
    await callback.answer(f"Статус изменения: {'Набор открыт' if new_status else 'Скрыто'}")

@router.callback_query(F.data.startswith("admin_delete_vac:"))
async def delete_vacancy_admin(callback: CallbackQuery):
    if not check_admin_permission(callback.from_user.id):
        await callback.answer("У вас нет прав.", show_alert=True)
        return
        
    vac_id = int(callback.data.split(":")[1])
    await delete_vacancy(vac_id)
    await callback.answer("Направление удалено!", show_alert=True)
    
    vacancies = await get_all_vacancies()
    if not vacancies:
        await callback.message.edit_text(
            "📋 **Список направлений пуст.**",
            reply_markup=get_admin_main_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await callback.message.edit_text(
            "📋 **Список всех направлений:**",
            reply_markup=get_admin_vacancies_keyboard(vacancies),
            parse_mode="Markdown"
        )


# --- СТАТИСТИКА ---

@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    if not check_admin_permission(callback.from_user.id):
        await callback.answer("У вас нет прав.", show_alert=True)
        return

    stats = await get_stats()

    text = (
        "📊 **Статистика бота**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👥 **Посещения (/start):**\n"
        f"  • Сегодня: **{stats['visits_today']}**\n"
        f"  • Вчера: **{stats['visits_yesterday']}**\n"
        f"  • За неделю: **{stats['visits_week']}** "
        f"(уникальных: {stats['unique_users_week']})\n\n"
        "📝 **Отправленные заявки:**\n"
        f"  • Сегодня: **{stats['apps_today']}**\n"
        f"  • Вчера: **{stats['apps_yesterday']}**\n"
        f"  • За неделю: **{stats['apps_week']}**\n"
        f"  • Всего: **{stats['apps_total']}**\n\n"
    )

    if stats['unsent_count'] > 0:
        text += (
            f"⚠️ **Не дошло до группы: {stats['unsent_count']} шт.**\n"
            "Нажмите «🔄 Переслать незашедшие заявки» чтобы отправить их."
        )
    else:
        text += "✅ Все заявки дошли до группы."

    from keyboards.inline import get_admin_main_keyboard
    try:
        await callback.message.edit_text(text, reply_markup=get_admin_main_keyboard(), parse_mode="Markdown")
    except Exception:
        await callback.message.answer(text, reply_markup=get_admin_main_keyboard(), parse_mode="Markdown")
    await callback.answer()


# --- ПЕРЕСЛАТЬ НЕОТПРАВЛЕННЫЕ ЗАЯВКИ ---

@router.callback_query(F.data == "admin_resend_unsent")
async def cb_admin_resend_unsent(callback: CallbackQuery, bot: Bot):
    if not check_admin_permission(callback.from_user.id):
        await callback.answer("У вас нет прав.", show_alert=True)
        return

    await callback.answer()

    if not TARGET_GROUP_ID or TARGET_GROUP_ID == 0:
        await callback.message.answer("❌ TARGET\_GROUP\_ID не задан. Невозможно отправить.")
        return

    unsent = await get_unsent_applications()
    if not unsent:
        await callback.message.answer("✅ Все заявки уже были отправлены в группу!")
        return

    await callback.message.answer(
        f"🔄 Найдено **{len(unsent)}** недошедших заявок. Начинаю отправку...",
        parse_mode="Markdown"
    )

    from keyboards.inline import get_group_application_keyboard

    sent_ok = 0
    sent_fail = 0

    for app in unsent:
        app_id  = app["id"]
        user_id = app["user_id"]
        username_str = f"@{app['username']}" if app.get("username") else "Отсутствует"

        card_text = (
            f"🎯 *НА КАКУЮ РОЛЬ:*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔥 *{app['vacancy_title']}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📋 *ДАННЫЕ КАНДИДАТА:*\n"
            f"👤 *ФИО:* {app['full_name']}\n"
            f"🎓 *Курс:* {app['course']}\n"
            f"🪦 *Student ID:* `{app['student_id']}`\n"
            f"✈️ *Telegram:* {username_str} (ID: `{user_id}`)\n"
            f"📞 *Контакты:* {app['contact_info']}\n"
            f"📄 *CV:* {app['cv_portfolio']}\n"
            f"🌐 *Язык:* {app.get('lang', 'ru').upper()}\n\n"
            f"🧠 *Мотивация:*\n{app['motivation']}\n\n"
            f"🔖 _Анкета \u2116{app_id} (✅ переотправка)_"
        )

        try:
            await bot.send_message(
                chat_id=TARGET_GROUP_ID,
                text=card_text,
                reply_markup=get_group_application_keyboard(app_id, user_id, app.get("username")),
                parse_mode="Markdown"
            )
            await mark_application_sent(app_id)
            sent_ok += 1
            logger.info(f"[Переотправка] Заявка #{app_id} успешно отправлена.")
        except Exception as e:
            # Fallback: без Markdown
            try:
                plain = (
                    f"🎯 {app['vacancy_title']}\n"
                    f"👤 {app['full_name']} | 🎓 {app['course']} | 🪦 {app['student_id']}\n"
                    f"✈️ {username_str} (ID: {user_id})\n"
                    f"📞 {app['contact_info']}\n"
                    f"📄 {app['cv_portfolio']}\n"
                    f"🧠 {app['motivation']}\n"
                    f"🔖 Анкета \u2116{app_id} (переотправка)"
                )
                await bot.send_message(
                    chat_id=TARGET_GROUP_ID,
                    text=plain,
                    reply_markup=get_group_application_keyboard(app_id, user_id, app.get("username"))
                )
                await mark_application_sent(app_id)
                sent_ok += 1
                logger.info(f"[Переотправка] Заявка #{app_id} отправлена (plain text).")
            except Exception as e2:
                sent_fail += 1
                logger.error(f"[Переотправка] Ошибка заявки #{app_id}: {e2}")

    result = f"✅ Отправлено: **{sent_ok}**\n"
    if sent_fail > 0:
        result += f"❌ Не удалось: **{sent_fail}** (см. логи)"
    await callback.message.answer(result, parse_mode="Markdown")
