import random
import hashlib
import streamlit as st
import pandas as pd
from sqlalchemy import text
from database.connection import get_db_engine, get_db_session

# ==============================================================================
# БЛОК 1: БЕЗОПАСНОСТЬ И АВТОРИЗАЦИЯ ПОЛЬЗОВАТЕЛЕЙ
# ==============================================================================

def hash_password(password: str) -> str:
    """Хэширует пароль с использованием алгоритма SHA-256."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def register_user(username: str, password: str) -> bool:
    """
    Регистрирует нового пользователя в системе.
    Возвращает False, если имя пользователя уже занято.
    """
    session = get_db_session()
    query = text("""
        INSERT INTO users (username, password_hash)
        VALUES (:username, :password_hash)
        ON CONFLICT (username) DO NOTHING
    """)
    try:
        result = session.execute(query, {
            "username": username.strip(),
            "password_hash": hash_password(password)
        })
        session.commit()
        # Если rowcount == 0, значит сработал ON CONFLICT и запись не была создана
        return result.rowcount > 0
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def authenticate_user(username: str, password: str):
    """
    Проверяет логин и пароль пользователя.
    Возвращает словарь с id и username при успехе, либо None при ошибке.
    """
    session = get_db_session()
    query = text("""
        SELECT id, username 
        FROM users 
        WHERE username = :username AND password_hash = :password_hash
    """)
    try:
        user = session.execute(query, {
            "username": username.strip(),
            "password_hash": hash_password(password)
        }).fetchone()

        if user:
            return {"id": user.id, "username": user.username}
        return None
    finally:
        session.close()


# ==============================================================================
# БЛОК 2: РАБОТА СО СЛОВАРЕМ И ЛОГИКА ТЕСТИРОВАНИЯ
# ==============================================================================

def get_available_words(user_id: int):
    """
    Возвращает полный список слов, доступных конкретному пользователю:
    Общие слова (минус удаленные им лично) + его персональные добавленные слова.
    """
    engine = get_db_engine()

    # 1. Запрос на получение общих слов, которые данный пользователь не скрывал
    global_query = text("""
        SELECT id, word_en, word_ru, 'global' as type 
        FROM global_words 
        WHERE id NOT IN (
            SELECT global_word_id FROM user_deleted_words WHERE user_id = :user_id
        )
    """)

    # 2. Запрос на получение личных слов пользователя
    custom_query = text("""
        SELECT id, word_en, word_ru, 'custom' as type 
        FROM user_custom_words 
        WHERE user_id = :user_id
    """)

    words = []
    with engine.connect() as conn:
        global_res = conn.execute(global_query, {"user_id": user_id}).fetchall()
        custom_res = conn.execute(custom_query, {"user_id": user_id}).fetchall()

        # Преобразуем результаты в удобный список словарей для фронтенда
        for row in global_res + custom_res:
            words.append({
                "id": row.id,
                "en": row.word_en,
                "ru": row.word_ru,
                "type": row.type
            })

    return words

def generate_quiz_options(user_id: int, current_word: dict):
    """
    Формирует список из 4 вариантов ответа на английском языке.
    Один ответ правильный, остальные три — случайные слова из общего пула.
    """
    engine = get_db_engine()

    # Собираем абсолютно все английские слова, о существовании которых знает база
    mix_query = text("""
        SELECT word_en FROM global_words
        UNION
        SELECT word_en FROM user_custom_words WHERE user_id = :user_id
    """)

    with engine.connect() as conn:
        result = conn.execute(mix_query, {"user_id": user_id}).fetchall()
        all_en_words = [row.word_en for row in result]

    # Исключаем правильный ответ из пула вариантов для подмены
    if current_word["en"] in all_en_words:
        all_en_words.remove(current_word["en"])

    # Выбираем до 3 случайных неправильных ответов из оставшихся
    wrong_options = random.sample(all_en_words, min(3, len(all_en_words)))

    # Объединяем правильный ответ с неправильными и тщательно перемешиваем пул
    options = wrong_options + [current_word["en"]]
    random.shuffle(options)
    return options


# ==============================================================================
# БЛОК 3: УПРАВЛЕНИЕ СЛОВАМИ (ДОБАВЛЕНИЕ И ПЕРСОНАЛЬНОЕ УДАЛЕНИЕ)
# ==============================================================================

def add_custom_word(user_id: int, word_en: str, word_ru: str):
    """
    Добавляет новое слово в персональный словарь пользователя.
    Это слово не будет отображаться у других зарегистрированных студентов.
    """
    session = get_db_session()
    query = text("""
        INSERT INTO user_custom_words (user_id, word_en, word_ru)
        VALUES (:user_id, :en, :ru)
        ON CONFLICT (user_id, word_en) DO NOTHING
    """)
    try:
        session.execute(query, {
            "user_id": user_id,
            "en": word_en.strip().lower(),
            "ru": word_ru.strip().lower()
        })
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def delete_word_for_user(user_id: int, word: dict):
    """
    Удаляет слово персонально для конкретного пользователя.
    Если слово глобальное — оно отправляется в локальный черный список.
    Если слово кастомное — оно физически стирается из его личного набора.
    """
    session = get_db_session()
    try:
        if word["type"] == "global":
            # Если слово из базового пакета, заносим его ID в таблицу исключений
            query = text("""
                INSERT INTO user_deleted_words (user_id, global_word_id)
                VALUES (:user_id, :word_id)
                ON CONFLICT DO NOTHING
            """)
            session.execute(query, {"user_id": user_id, "word_id": word["id"]})
        else:
            # Если слово было создано самим пользователем, физически удаляем запись
            query = text("""
                DELETE FROM user_custom_words 
                WHERE user_id = :user_id AND id = :word_id
            """)
            session.execute(query, {"user_id": user_id, "word_id": word["id"]})
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def get_user_words_count(user_id: int) -> int:
    """Возвращает общее количество слов, которые сейчас изучаются пользователем."""
    # Вызываем ранее написанную функцию, которая уже считает (Глобальные - Удаленные + Кастомные)
    words = get_available_words(user_id)
    return len(words)

def log_user_answer(user_id: int, is_correct: bool):
    """Записывает результат ответа пользователя в таблицу статистики."""
    session = get_db_session()
    query = text("""
        INSERT INTO user_stats (user_id, is_correct, answered_at)
        VALUES (:user_id, :is_correct, CURRENT_TIMESTAMP)
    """)
    try:
        session.execute(query, {"user_id": user_id, "is_correct": is_correct})
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def get_user_statistics(user_id: int):
    """Возвращает количество правильных ответов и общую точность (в %)."""
    engine = get_db_engine()
    query = text("""
        SELECT 
            COUNT(*) FILTER (WHERE is_correct = TRUE) as correct_answers,
            COUNT(*) as total_answers
        FROM user_stats
        WHERE user_id = :user_id
    """)
    with engine.connect() as conn:
        res = conn.execute(query, {"user_id": user_id}).fetchone()

    if res and res.total_answers > 0:
        accuracy = round((res.correct_answers / res.total_answers) * 100, 1)
        return {
            "correct": res.correct_answers,
            "total": res.total_answers,
            "accuracy": accuracy
        }
    return {"correct": 0, "total": 0, "accuracy": 0.0}
