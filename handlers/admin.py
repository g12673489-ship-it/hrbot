from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from config import is_admin
from database.db import (
    create_vacancy,
    get_all_vacancies,
    get_vacancy_by_id,
    toggle_vacancy_active,
    delete_vacancy,
    get_user_lang
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
