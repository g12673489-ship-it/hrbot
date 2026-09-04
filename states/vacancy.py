from aiogram.fsm.state import State, StatesGroup

class VacancyForm(StatesGroup):
    title = State()        # Название направления / команды
    description = State()  # Описание направления
    requirements = State() # Кого мы ищем / требования
    photo = State()        # Фото направления (необязательно)
