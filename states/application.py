from aiogram.fsm.state import State, StatesGroup

class ApplicationForm(StatesGroup):
    full_name = State()     # ФИО студента
    course = State()        # Курс обучения
    student_id = State()    # Student ID
    contact_info = State()  # Телефон / Контакты
    cv_portfolio = State()  # Ссылка на CV / Портфолио (ixtiyoriy / по желанию)
    motivation = State()    # Мотивация / почему хочу в команду
    confirm = State()       # Подтверждение отправки
