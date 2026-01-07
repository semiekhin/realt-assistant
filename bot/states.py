"""
Состояния диалога (FSM)
"""


class States:
    """Состояния пользователя"""
    
    # Начальное / нет состояния
    IDLE = ""
    
    # Добавление ЖК
    ADD_PROPERTY_NAME = "add_property:name"        # Ожидаем название
    ADD_PROPERTY_FILES = "add_property:files"      # Ожидаем файлы
    ADD_PROPERTY_CONFIRM = "add_property:confirm"  # Подтверждение данных
    
    # Редактирование ЖК
    EDIT_PROPERTY = "edit_property"
    
    # Поиск
    SEARCH = "search"


# Текстовые команды для выхода из любого состояния
EXIT_COMMANDS = ["/cancel", "отмена", "выход", "назад"]


def is_exit_command(text: str) -> bool:
    """Проверить, является ли текст командой выхода"""
    return text.lower().strip() in EXIT_COMMANDS
