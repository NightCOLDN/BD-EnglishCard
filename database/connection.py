import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

@st.cache_resource
def get_db_engine():
    """Создает и кэширует пул подключений к PostgreSQL с явной кодировкой utf8."""
    cfg = st.secrets["postgres"]
    url = f"postgresql://{cfg['user']}:{cfg['password']}@{cfg['host']}:{cfg['port']}/{cfg['database']}"
    return create_engine(url, echo=False, connect_args={"client_encoding": "utf8"})

def get_db_session():
    """Возвращает новую сессию для выполнения транзакций в БД."""
    return sessionmaker(bind=get_db_engine())()

def init_db():
    """Автоматически создает все необходимые таблицы и стартовый словарь."""
    session = get_db_session()
    init_script = """
    CREATE TABLE IF NOT EXISTS user_stats (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        is_correct BOOLEAN NOT NULL,
        answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
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
        user_id INTEGER NOT NULL,
        word_en VARCHAR(100) NOT NULL,
        word_ru VARCHAR(100) NOT NULL,
        CONSTRAINT unique_user_custom_word UNIQUE (user_id, word_en)
    );
    CREATE TABLE IF NOT EXISTS user_deleted_words (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        global_word_id INTEGER REFERENCES global_words(id) ON DELETE CASCADE,
        CONSTRAINT unique_user_deleted UNIQUE (user_id, global_word_id)
    );
    INSERT INTO global_words (word_en, word_ru) VALUES
    ('red', 'красный'), ('blue', 'синий'), ('green', 'зеленый'),
    ('i', 'я'), ('you', 'ты'), ('he', 'он'),
    ('apple', 'яблоко'), ('cat', 'кошка'), ('dog', 'собака'), ('book', 'книга')
    ON CONFLICT (word_en) DO NOTHING;
    """
    try:
        session.execute(text(init_script))
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
