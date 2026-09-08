import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery

from database.db import get_application_by_id, update_application_status, mark_application_sent
from locales.texts import get_text

logger = logging.getLogger(__name__)
router = Router()


def _build_decision_text(original_text: str | None, status_line: str) -> str:
    """Добавляет строку о решении к тексту карточки."""
    base = original_text or ""
    return (
        f"{base}\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"{status_line}"
    )


@router.callback_query(F.data.startswith("group_accept:"))
async def cb_group_accept(callback: CallbackQuery, bot: Bot):
    app_id = int(callback.data.split(":")[1])
    app = await get_application_by_id(app_id)

    if not app:
        await callback.answer("Заявка не найдена в базе данных.", show_alert=True)
        return

    manager_name = callback.from_user.full_name
    await update_application_status(app_id, "accepted")

    status_line = f"✅ **СТАТУС: ПРИНЯТ В КОМАНДУ**\n👤 Решение принял(а): {manager_name}"
    updated_text = _build_decision_text(callback.message.text, status_line)

    try:
        await callback.message.edit_text(
            text=updated_text,
            reply_markup=None,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.warning(f"Не удалось изменить сообщение карточки #{app_id}: {e}")

    await callback.answer("Студент принят в команду!")

    # Уведомляем студента на его языке
    user_lang = app.get("lang", "ru")
    try:
        await bot.send_message(
            chat_id=app["user_id"],
            text=get_text(user_lang, "app_accepted_user", title=app["vacancy_title"]),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.warning(f"Не удалось отправить уведомление студенту {app['user_id']}: {e}")


@router.callback_query(F.data.startswith("group_reject:"))
async def cb_group_reject(callback: CallbackQuery, bot: Bot):
    app_id = int(callback.data.split(":")[1])
    app = await get_application_by_id(app_id)

    if not app:
        await callback.answer("Заявка не найдена в базе данных.", show_alert=True)
        return

    manager_name = callback.from_user.full_name
    await update_application_status(app_id, "rejected")

    status_line = f"❌ **СТАТУС: ОТКЛОНЕН**\n👤 Решение принял(а): {manager_name}"
    updated_text = _build_decision_text(callback.message.text, status_line)

    try:
        await callback.message.edit_text(
            text=updated_text,
            reply_markup=None,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.warning(f"Не удалось изменить сообщение карточки #{app_id}: {e}")

    await callback.answer("Заявка отклонена.")

    # Уведомляем студента на его языке
    user_lang = app.get("lang", "ru")
    try:
        await bot.send_message(
            chat_id=app["user_id"],
            text=get_text(user_lang, "app_rejected_user", title=app["vacancy_title"]),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.warning(f"Не удалось отправить уведомление студенту {app['user_id']}: {e}")
