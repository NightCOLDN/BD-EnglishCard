import logging
import sys

def setup_logger() -> logging.Logger:
    """Настраивает системный логер для вывода в консоль и записи ошибок в файл."""
    logger = logging.getLogger("EnglishCard")

    # Если логер уже настроен, не добавляем обработчики повторно
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # Формат записи: Дата Время [Уровень] Модуль: Сообщение
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(filename)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 1. Обработчик для вывода обычных логов в консоль (sys.stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

    # 2. Обработчик для записи только ОШИБОК (ERROR и выше) в файл app.log
    file_handler = logging.FileHandler("app.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.ERROR)
    logger.addHandler(file_handler)

    return logger

# Экспортируем готовый объект логера для использования в других файлах
log = setup_logger()
