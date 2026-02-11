from aiogram.fsm.state import State, StatesGroup


class BotState(StatesGroup):
    IDLE = State()      # режим ожидания / приёма новых текстов
    TRAIN = State()     # тренировка
    SEARCH = State()    # поиск
    STATS = State()     # просмотр статистики
