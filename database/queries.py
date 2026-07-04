import os
import sys
import random
import importlib.util
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from database.connection import get_db_session

# --- ВЫЧИСЛЕНИЕ ПУТЕЙ И ЖЕЛЕЗОБЕТОННЫЙ ИМПОРТ ИЗ ПАПКИ UTILS ---
current_dir = os.path.dirname(os.path.abspath(__file__))  # папка database
project_root = os.path.dirname(current_dir)               # корень проекта

# 1. Автономный импорт LOG
logger_path = os.path.join(project_root, "utils", "logger.py")
if os.path.exists(logger_path):
    spec_log = importlib.util.spec_from_file_location("logger", logger_path)
    utils_logger = importlib.util.module_from_spec(spec_log)
    spec_log.loader.exec_module(utils_logger)
    log = utils_logger.log
else:
    import logging
    log = logging.getLogger("Fallback")

# 2. Автономный импорт SECURITY (HASH_PASSWORD)
security_path = os.path.join(project_root, "utils", "security.py")
if os.path.exists(security_path):
    spec_sec = importlib.util.spec_from_file_location("security", security_path)
    utils_security = importlib.util.module_from_spec(spec_sec)
    spec_sec.loader.exec_module(utils_security)
    hash_password = utils_security.hash_password
else:
    log.warning("Файл security.py не найден! Применен резервный метод.")
    def hash_password(password: str) -> str: return password
# ---------------------------------------------------------------


# def get_quiz_round_data(user_id: int) -> Optional[Dict[str, Any]]:
#     """
#     Одним запросом извлекает 4 случайные пары слов, исключая удаленные пользователем.
#     Первая пара становится загадываемой, а оставшиеся три идут под варианты ответов.
#     """
#     quiz_query = text("""
#         SELECT word_en, word_ru
#         FROM (
#             SELECT word_en, word_ru FROM global_words
#             WHERE id NOT IN (
#                 SELECT global_word_id FROM user_deleted_words WHERE user_id = :user_id
#             )
#             UNION
#             SELECT word_en, word_ru FROM user_custom_words
#             WHERE user_id = :user_id
#         ) AS combined_words
#         ORDER BY RANDOM()
#         LIMIT 4;
#     """)
#
#     with get_db_session() as session:
#         rows = session.execute(quiz_query, {"user_id": user_id}).fetchall()
#
#     if len(rows) < 4:
#         log.warning(f"У пользователя ID {user_id} недостаточно слов в пуле для генерации викторины.")
#         return None
#
#     # Преобразуем ответ в список словарей с жесткой типизацией
#     words_pool: List[Dict[str, str]] = [{"en": r.word_en, "ru": r.word_ru} for r in rows]
#
#     # Первая пара — угадываемая
#     current_word = words_pool[0]
#
#     # Собираем 4 варианта ответов и перемешиваем их для кнопок интерфейса
#     options: List[str] = [w["en"] for w in words_pool]
#     random.shuffle(options)
#
#     return {
#         "current_word": current_word,
#         "options": options
#     }
def get_quiz_round_data(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Умный запрос раунда: собирает 4 пары слов, но сортирует их так,
    чтобы кастомные (новые личные) слова пользователя шли в приоритете
    над общим базовым словарем, обеспечивая интервальное заучивание.
    """
    log.info(f"[DB_FETCH] Инициализирован умный запрос раунда для user_id={user_id}")

    # SQL-запрос разделяет пул на глобальные и личные, помечая личные высшим приоритетом (is_custom = 1)
    quiz_query = text("""
        SELECT word_en, word_ru, is_custom
        FROM (
            SELECT word_en, word_ru, 0 AS is_custom FROM global_words
            WHERE id NOT IN (
                SELECT global_word_id FROM user_deleted_words WHERE user_id = :user_id
            )
            UNION
            SELECT word_en, word_ru, 1 AS is_custom FROM user_custom_words 
            WHERE user_id = :user_id
        ) AS combined_words
        ORDER BY 
            is_custom DESC, -- Сначала отдаем в тест личные добавленные слова
            RANDOM()        -- Внутри групп перемешиваем случайно
        LIMIT 4;
    """)

    try:
        with get_db_session() as session:
            rows = session.execute(quiz_query, {"user_id": user_id}).fetchall()
        log.info(f"[DB_FETCH] Успешно получено строк: {len(rows)} для user_id={user_id}")
    except OperationalError as e:
        log.error(f"[DB_CRITICAL] База данных недоступна при запросе раунда для user_id={user_id}. Ошибка: {e}")
        return None

    if len(rows) < 4:
        log.warning(f"[QUIZ_WARN] Недостаточно слов (всего {len(rows)} из 4 необходимых) для user_id={user_id}")
        return None

    # Преобразуем ответ в список словарей
    words_pool: List[Dict[str, str]] = [{"en": r.word_en, "ru": r.word_ru} for r in rows]

    # Благодаря сортировке 'is_custom DESC', если у пользователя есть личные слова,
    # первое слово (которое станет загадываемым) гарантированно будет его новым личным словом!
    current_word = words_pool[0]

    # Вариантами ответов становятся все 4 извлеченных слова
    options: List[str] = [w["en"] for w in words_pool]
    # Тщательно перемешиваем варианты, чтобы правильный ответ не всегда был на первой кнопке
    random.shuffle(options)

    return {
        "current_word": current_word,
        "options": options
    }


def add_custom_word(user_id: int, word_en: str, word_ru: str) -> str:
    """
    Добавляет слово в личный словарь.
    Безопасно фиксирует транзакцию (commit) внутри изолированного контекста сессии.
    """
    check_global = text("SELECT 1 FROM global_words WHERE LOWER(word_en) = :word_en LIMIT 1;")
    check_custom = text("SELECT 1 FROM user_custom_words WHERE user_id = :user_id AND LOWER(word_en) = :word_en LIMIT 1;")
    insert_query = text("INSERT INTO user_custom_words (user_id, word_en, word_ru) VALUES (:user_id, :word_en, :word_ru);")

    with get_db_session() as session:
        if session.execute(check_global, {"word_en": word_en}).fetchone():
            return "global_exists"

        if session.execute(check_custom, {"user_id": user_id, "word_en": word_en}).fetchone():
            return "custom_exists"

        session.execute(insert_query, {"user_id": user_id, "word_en": word_en, "word_ru": word_ru})
        session.commit()

    log.info(f"Пользователь ID {user_id} успешно добавил кастомное слово: '{word_en}'")
    return "success"


def register_user(username: str, password_raw: str) -> bool:
    """Чистая регистрация пользователя с автоматическим управлением транзакцией базы данных."""
    check_user = text("SELECT 1 FROM users WHERE LOWER(username) = LOWER(:username) LIMIT 1;")
    insert_user = text("INSERT INTO users (username, password_hash) VALUES (:username, :password_hash);")

    password_hash = hash_password(password_raw)

    with get_db_session() as session:
        if session.execute(check_user, {"username": username}).fetchone():
            return False

        session.execute(insert_user, {"username": username, "password_hash": password_hash})
        session.commit()

    log.info(f"Зарегистрирован новый пользователь: '{username}'")
    return True


def authenticate_user(username: str, password_raw: str) -> Optional[Dict[str, Any]]:
    """Проверяет учетные данные пользователя, сравнивая хеши паролей."""
    query = text("SELECT id, username FROM users WHERE LOWER(username) = LOWER(:username) AND password_hash = :password_hash LIMIT 1;")
    target_hash = hash_password(password_raw)

    with get_db_session() as session:
        result = session.execute(query, {"username": username, "password_hash": target_hash}).fetchone()

    if result:
        log.info(f"Успешная авторизация пользователя: '{username}' (ID: {result.id})")
        return {"id": result.id, "username": result.username}

    log.warning(f"Неудачная попытка входа под именем: '{username}'")
    return None


def delete_word_for_user(user_id: int, current_word: Dict[str, str]) -> None:
    """
    Персонально скрывает (удаляет) слово для конкретного пользователя.
    Если слово кастомное — удаляет его физически.
    Если слово базовое (global) — заносит его ID в таблицу исключений user_deleted_words.
    """
    with get_db_session() as session:
        # 1. Проверяем, является ли слово кастомным словом этого пользователя
        check_custom = text("""
            SELECT id FROM user_custom_words 
            WHERE user_id = :user_id AND word_en = :word_en LIMIT 1;
        """)
        custom_row = session.execute(check_custom, {"user_id": user_id, "word_en": current_word["en"]}).fetchone()

        if custom_row:
            delete_custom = text("DELETE FROM user_custom_words WHERE id = :id;")
            session.execute(delete_custom, {"id": custom_row.id})
            session.commit()
            log.info(f"Пользователь ID {user_id} навсегда удалил личное слово '{current_word['en']}'.")
            return

        # 2. Если слова нет в личных, находим его ID в глобальных
        check_global = text("SELECT id FROM global_words WHERE word_en = :word_en LIMIT 1;")
        global_row = session.execute(check_global, {"word_en": current_word["en"]}).fetchone()

        if global_row:
            check_deleted = text("""
                SELECT 1 FROM user_deleted_words 
                WHERE user_id = :user_id AND global_word_id = :global_id LIMIT 1;
            """)
            if not session.execute(check_deleted, {"user_id": user_id, "global_id": global_row.id}).fetchone():
                insert_deleted = text("""
                    INSERT INTO user_deleted_words (user_id, global_word_id) 
                    VALUES (:user_id, :global_id);
                """)
                session.execute(insert_deleted, {"user_id": user_id, "global_id": global_row.id})
                session.commit()
                log.info(f"Пользователь ID {user_id} скрыл глобальное слово '{current_word['en']}'.")


def log_user_answer(user_id: int, is_correct: bool) -> None:
    """Записывает результат ответа пользователя (правильно/неправильно) в таблицу статистики."""
    insert_stat = text("""
        INSERT INTO user_stats (user_id, is_correct) 
        VALUES (:user_id, :is_correct);
    """)
    with get_db_session() as session:
        session.execute(insert_stat, {"user_id": user_id, "is_correct": is_correct})
        session.commit()


def get_user_statistics(user_id: int) -> Dict[str, int]:
    """Вычисляет общую статистику ответов пользователя (всего, правильных и процент точности)."""
    query = text("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct
        FROM user_stats 
        WHERE user_id = :user_id;
    """)
    with get_db_session() as session:
        row = session.execute(query, {"user_id": user_id}).fetchone()

    total = row.total if row and row.total else 0
    correct = row.correct if row and row.correct else 0
    accuracy = round((correct / total) * 100) if total > 0 else 0

    return {
        "total": total,
        "correct": correct,
        "accuracy": accuracy
    }


def get_user_words_count(user_id: int) -> int:
    """Возвращает общее число слов, доступных пользователю в обучении (глобальные минус удаленные плюс личные)."""
    # 1. Считаем глобальные доступные слова
    query_global = text("""
        SELECT COUNT(*) FROM global_words 
        WHERE id NOT IN (SELECT global_word_id FROM user_deleted_words WHERE user_id = :user_id);
    """)
    # 2. Считаем личные кастомные слова
    query_custom = text("SELECT COUNT(*) FROM user_custom_words WHERE user_id = :user_id;")

    with get_db_session() as session:
        global_count = session.execute(query_global, {"user_id": user_id}).scalar() or 0
        custom_count = session.execute(query_custom, {"user_id": user_id}).scalar() or 0

    return global_count + custom_count
