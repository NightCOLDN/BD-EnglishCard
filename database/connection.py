import os
import sys
import importlib.util

# 1. Вычисляем точный физический путь к файлу logger.py на диске D:
current_dir = os.path.dirname(os.path.abspath(__file__)) # папка database
project_root = os.path.dirname(current_dir)              # корень проекта
logger_path = os.path.join(project_root, "utils", "logger.py")

# 2. Железобетонный автономный импорт файла по его прямому адресу на диске
if os.path.exists(logger_path):
    spec = importlib.util.spec_from_file_location("logger", logger_path)
    utils_logger = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(utils_logger)
    log = utils_logger.log
else:
    # Запасной вариант, если папка utils переименована или отсутствует
    import logging
    log = logging.getLogger("Fallback")

# 3. Теперь импортируем сторонние библиотеки
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
def get_db_engine():
    """Создает и кэширует пул подключений к PostgreSQL с явной кодировкой utf8."""
    cfg = st.secrets["postgres"]
    url = f"postgresql://{cfg['user']}:{cfg['password']}@{cfg['host']}:{cfg['port']}/{cfg['database']}"
    return create_engine(url, echo=False, connect_args={"client_encoding": "utf8"})

def get_db_session():
    """Возвращает новую сессию для выполнения транзакций в БД."""
    return sessionmaker(bind=get_db_engine())()

def init_db() -> None:
    """Автоматически создает все необходимые таблицы с внешними ключами."""
    session = get_db_session()
    init_script = """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL
    );
    CREATE TABLE IF NOT EXISTS global_words (
        id SERIAL PRIMARY KEY,
        word_en VARCHAR(100) NOT NULL UNIQUE,
        word_ru VARCHAR(100) NOT NULL
    );
    CREATE TABLE IF NOT EXISTS user_custom_words (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        word_en VARCHAR(100) NOT NULL,
        word_ru VARCHAR(100) NOT NULL,
        CONSTRAINT unique_user_custom_word UNIQUE (user_id, word_en)
    );
    CREATE TABLE IF NOT EXISTS user_deleted_words (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        global_word_id INTEGER REFERENCES global_words(id) ON DELETE CASCADE,
        CONSTRAINT unique_user_deleted UNIQUE (user_id, global_word_id)
    );
    CREATE TABLE IF NOT EXISTS user_stats (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        is_correct BOOLEAN NOT NULL,
        answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    INSERT INTO global_words (word_en, word_ru) VALUES
    ('red', 'красный'), ('blue', 'синий'), ('green', 'зеленый'),
    ('i', 'я'), ('you', 'ты'), ('he', 'он'),
    ('apple', 'яблоко'), ('cat', 'кошка'), ('dog', 'собака'), ('book', 'книга')
    ON CONFLICT (word_en) DO NOTHING;
    """
    session.execute(text(init_script))
    session.commit()
    session.close()
    log.info("База данных успешно инициализирована!")

# Точка запуска инициализации структуры БД из терминала (python connection.py)
if __name__ == '__main__':
    init_db()
