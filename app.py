import os
import sys
from typing import List, Dict, Any, Optional

# Фиксируем корень проекта
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
import pandas as pd
import re
from database.connection import get_db_engine, get_db_session
from database.schema import DATABASE_SCHEMA_TEXT
from sqlalchemy import text
from database.queries import (
    get_quiz_round_data,
    add_custom_word,
    delete_word_for_user,
    log_user_answer,
    get_user_statistics,
    get_user_words_count
)
# Импорт сопутствующих конфигураций и служебных модулей
from config import QUESTIONS_PER_ROUND
from utils.state import init_session_states, reset_session_logout
from utils.effects import trigger_confetti, play_success_sound
from components.auth import run_authentication
from utils.logger import log


def next_question() -> None:
    """Обновляет состояние карточки, запрашивая новые 4 случайные пары одной строкой."""
    if not st.session_state.user_info:
        return

    if st.session_state.round_question_count >= QUESTIONS_PER_ROUND:
        st.session_state.round_finished = True
        st.session_state.current_word = None
        return

    user_id: int = st.session_state.user_info["id"]
    quiz_data: Optional[Dict[str, Any]] = get_quiz_round_data(user_id)

    if not quiz_data:
        st.session_state.current_word = None
        st.session_state.options = []
        st.session_state.answer_status = None
        return

    st.session_state.round_question_count += 1
    st.session_state.current_word = quiz_data["current_word"]
    st.session_state.options = quiz_data["options"]
    st.session_state.answer_status = None
    st.session_state.current_word_fault = False

def lern_func(user_id: int) -> None:
    """Логика вкладки 1: Изучение слов в стиле Минималистичный Премиум."""
    st.header("🎯 Изучаем слова")

    if st.session_state.round_finished:
        st.balloons()
        st.success("🎉 Поздравляем! Вы завершили раунд обучения!")
        score_percent: int = round((st.session_state.round_correct_count / QUESTIONS_PER_ROUND) * 100)

        # Элегантные минималистичные карточки результатов
        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.markdown(
                f"""
                <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 15px; border-radius: 8px; text-align: center;">
                    <p style="margin: 0; color: #64748B; font-size: 14px; font-weight: 500;">Показано слов</p>
                    <p style="margin: 5px 0 0 0; color: #0F172A; font-size: 24px; font-weight: 600;">{QUESTIONS_PER_ROUND}</p>
                </div>
                """, unsafe_allow_html=True
            )
        with res_col2:
            st.markdown(
                f"""
                <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 15px; border-radius: 8px; text-align: center;">
                    <p style="margin: 0; color: #64748B; font-size: 14px; font-weight: 500;">Правильных ответов</p>
                    <p style="margin: 5px 0 0 0; color: #0F172A; font-size: 24px; font-weight: 600;">{st.session_state.round_correct_count} из {QUESTIONS_PER_ROUND}</p>
                </div>
                """, unsafe_allow_html=True
            )

        st.markdown(f"<p style='color: #475569; margin-top: 15px;'>Ваша точность в этом раунде: <b>{score_percent}%</b></p>", unsafe_allow_html=True)
        if st.button("🔄 Начать новый раунд", type="primary", use_container_width=True):
            st.session_state.round_question_count = 0
            st.session_state.round_correct_count = 0
            st.session_state.round_finished = False
            next_question()
            st.rerun()

    elif st.session_state.current_word:
        # Тонкий аккуратный Progress Bar
        progress_percentage = min(st.session_state.round_question_count / QUESTIONS_PER_ROUND, 1.0)
        st.progress(progress_percentage)
        st.caption(f"Вопрос {st.session_state.round_question_count} из {QUESTIONS_PER_ROUND}")

        # Элегантная белая карточка с тонкой рамкой и мягкой тенью
        ru_word: str = st.session_state.current_word['ru'].lower()
        st.markdown(
            f"""
            <div style="
                display: flex; 
                justify-content: center; 
                align-items: center; 
                width: 100%; 
                background-color: #FFFFFF; 
                border: 1px solid #E2E8F0;
                padding: 25px 0px; 
                border-radius: 10px; 
                margin-top: 10px;
                margin-bottom: 25px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            ">
                <h1 style="color: #0F172A; margin: 0; font-size: 32px; text-transform: capitalize; font-weight: 600; letter-spacing: -0.5px;">
                    {ru_word}
                </h1>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("<p style='text-align: center; color: #64748B; font-size: 20px; margin-bottom: 20px;'>Выберите правильный перевод слова на английский язык:</p>", unsafe_allow_html=True)

        # Тонкие минималистичные кнопки вариантов ответов
        st.markdown(
            """
            <style>
                div.stButton > button {
                    font-size: 16px !important;
                    font-weight: 500 !important;
                    background-color: #FFFFFF !important;
                    color: #334155 !important;
                    border: 1px solid #E2E8F0 !important;
                    padding: 10px 20px !important;
                    border-radius: 8px !important;
                    transition: all 0.15s ease-in-out !important;
                }
                div.stButton > button:hover {
                    border-color: #94A3B8 !important;
                    background-color: #F8FAFC !important;
                    color: #0F172A !important;
                }
            </style>
            """,
            unsafe_allow_html=True
        )

        cols = st.columns(4)
        for i, option in enumerate(st.session_state.options):
            with cols[i]:
                is_disabled: bool = (st.session_state.answer_status == "correct")
                if st.button(option, key=f"opt_{option}_{i}", use_container_width=True, disabled=is_disabled):
                    if option == st.session_state.current_word["en"]:
                        st.session_state.answer_status = "correct"
                        log_user_answer(user_id, True)
                        if not st.session_state.current_word_fault:
                            st.session_state.round_correct_count += 1
                    else:
                        st.session_state.answer_status = "incorrect"
                        log_user_answer(user_id, False)
                        st.session_state.current_word_fault = True
                    st.rerun()

        if st.session_state.answer_status == "correct":
            st.markdown("<br>", unsafe_allow_html=True)
            _, center_col, _ = st.columns([1, 2, 1])
            with center_col:
                if st.button("➡️ Следующее слово", type="primary", use_container_width=True):
                    next_question()
                    st.rerun()
    else:
        st.warning("⚠️ В вашем словаре не осталось доступных слов для изучения!")

    st.markdown("---")
    with st.expander("📊 Посмотреть схему базы данных (Database Schema)"):
        st.code(DATABASE_SCHEMA_TEXT, language="text")

# def add_word_func(user_id: int) -> None:
#     """Логика вкладки 2: Добавление нового слова в горизонтальной сетке Clean-стиля."""
#     st.header("➕ Добавление слова")
#     st.markdown("<p style='color: #64748B; margin-bottom: 20px;'>Введите слово и его перевод для расширения вашего личного словаря.</p>", unsafe_allow_html=True)
#
#     with st.form(key="add_word_form", clear_on_submit=True):
#         # Располагаем поля в элегантную двухколоночную сетку
#         col_ru, col_en = st.columns(2)
#         with col_ru:
#             new_ru = st.text_input("Слово на русском:", placeholder="например, собака")
#         with col_en:
#             new_en = st.text_input("Перевод на английский:", placeholder="например, dog")
#
#         # Аккуратное смещение кнопки вправо
#         _, btn_col = st.columns([3, 1])
#         with btn_col:
#             submit_word = st.form_submit_button("Сохранить слово", type="primary", use_container_width=True)
#
#     if submit_word:
#         cleaned_ru = new_ru.strip().lower()
#         cleaned_en = new_en.strip().lower()
#
#         if not cleaned_ru or not cleaned_en:
#             st.warning("Пожалуйста, заполните оба поля.")
#         elif not cleaned_en.isascii():
#             st.error("Английское слово должно быть написано латинскими буквами!")
#         else:
#             result = add_custom_word(user_id, cleaned_en, cleaned_ru)
#             if result == "success":
#                 st.success(f"Слово '{cleaned_en}' успешно добавлено в ваш словарь!")
#                 next_question()
#                 st.rerun()
#             elif result == "global_exists":
#                 st.error(f"Слово '{cleaned_en}' уже есть в общем базовом словаре!")
#             elif result == "custom_exists":
#                 st.warning(f"Вы уже добавляли слово '{cleaned_en}' в личный словарь ранее.")
def add_word_func(user_id: int) -> None:
    """Логика вкладки 2: Добавление нового слова с жесткой валидацией кириллицы/латиницы."""
    st.header("➕ Добавление слова")
    st.markdown("<p style='color: #64748B; margin-bottom: 20px;'>Введите слово и его перевод для расширения вашего личного словаря.</p>", unsafe_allow_html=True)

    with st.form(key="add_word_form", clear_on_submit=True):
        col_ru, col_en = st.columns(2)
        with col_ru:
            new_ru = st.text_input("Слово на русском:", placeholder="например, собака")
        with col_en:
            new_en = st.text_input("Перевод на английский:", placeholder="например, dog")

        _, btn_col = st.columns()
        with btn_col:
            submit_word = st.form_submit_button("Сохранить слово", type="primary", use_container_width=True)

    if submit_word:
        # Элегантная очистка от случайных пробелов по краям и перевод в нижний регистр
        cleaned_ru = new_ru.strip().lower()
        cleaned_en = new_en.strip().lower()

        # Регулярные выражения: только буквы и дефис (для составных слов типа "он-лайн" или "ice-cream")
        cyrillic_pattern = re.compile(r"^[а-яё\-]+$")
        latin_pattern = re.compile(r"^[a-z\-]+$")

        if not cleaned_ru or not cleaned_en:
            st.warning("⚠️ Пожалуйста, заполните оба поля.")
        # Валидация русского поля
        elif not cyrillic_pattern.match(cleaned_ru):
            st.error("❌ Поле 'Слово на русском' должно содержать только русские буквы (кириллицу) без цифр и символов!")
        # Валидация английского поля
        elif not latin_pattern.match(cleaned_en):
            st.error("❌ Поле 'Перевод на английский' должно содержать только английские буквы (латиницу) без цифр и символов!")
        else:
            # Если валидация успешна, отправляем чистые данные в базу
            result = add_custom_word(user_id, cleaned_en, cleaned_ru)
            if result == "success":
                st.success(f"🎉 Слово '{cleaned_en}' успешно добавлено в ваш словарь!")
                next_question()
                st.rerun()
            elif result == "global_exists":
                st.error(f"ℹ️ Слово '{cleaned_en}' уже есть в общем базовом словаре!")
            elif result == "custom_exists":
                st.warning(f"⚠️ Вы уже добавляли слово '{cleaned_en}' в личный словарь ранее.")

def delete_word_func(user_id: int) -> None:
    """Логика вкладки 3: Персональное сдержанное удаление слов."""
    st.header("🗑️ Исключение слов")
    st.markdown("<p style='color: #64748B; margin-bottom: 20px;'>Если вы уже идеально запомнили слово, вы можете временно убрать его из текущего пула обучения.</p>", unsafe_allow_html=True)

    if st.session_state.current_word:
        # Карточка-информатор
        st.markdown(
            f"""
            <div style="background-color: #F8FAFC; border-left: 4px solid #94A3B8; padding: 15px; border-radius: 4px; margin-bottom: 20px;">
                <span style="color: #475569; font-size: 15px;">Текущее выбранное слово: </span>
                <strong style="color: #0F172A; font-size: 16px; text-transform: capitalize;">{st.session_state.current_word['ru']}</strong>
            </div>
            """, unsafe_allow_html=True
        )

        _, btn_col = st.columns([2, 1])
        with btn_col:
            # Сдержанная кнопка вместо агрессивного красного цвета
            if st.button("Удалить текущее слово", type="secondary", use_container_width=True, key="delete_current_word"):
                delete_word_for_user(user_id, st.session_state.current_word)
                st.toast("Слово скрыто из вашего словаря!")
                next_question()
                st.rerun()
    else:
        st.write("Нет доступных слов для удаления.")

def stats_func(user_id: int) -> None:
    """Логика вкладки 4: Статистика в стиле благородного аналитического дашборда."""
    st.header("📈 Ваша статистика обучения")
    stats = get_user_statistics(user_id)
    total_words = get_user_words_count(user_id)

    # Минималистичные карточки метрик с тонкими границами и мягкими тенями
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1:
        st.markdown(
            f"""
            <div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; padding: 18px; border-radius: 8px; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05);">
                <p style="margin: 0; color: #64748B; font-size: 13px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;">📚 Слов в обучении</p>
                <p style="margin: 8px 0 0 0; color: #0F172A; font-size: 28px; font-weight: 600;">{total_words}</p>
            </div>
            """, unsafe_allow_html=True
        )
    with m_col2:
        st.markdown(
            f"""
            <div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; padding: 18px; border-radius: 8px; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05);">
                <p style="margin: 0; color: #64748B; font-size: 13px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;">🎯 Верных ответов</p>
                <p style="margin: 8px 0 0 0; color: #10B981; font-size: 28px; font-weight: 600;">{stats['correct']}</p>
            </div>
            """, unsafe_allow_html=True
        )
    with m_col3:
        st.markdown(
            f"""
            <div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; padding: 18px; border-radius: 8px; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05);">
                <p style="margin: 0; color: #64748B; font-size: 13px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;">📊 Точность ответов</p>
                <p style="margin: 8px 0 0 0; color: #2563EB; font-size: 28px; font-weight: 600;">{stats['accuracy']}%</p>
            </div>
            """, unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    if stats["total"] > 0:
        st.markdown(f"<p style='color: #475569; font-size: 14px;'>Общий прогресс точности (всего ответов: {stats['total']}):</p>", unsafe_allow_html=True)
        st.progress(stats["accuracy"] / 100.0)

        # Контекстный менеджер для безопасного извлечения данных под график активности
        with get_db_session() as session:
            df = pd.read_sql(
                text("SELECT answered_at::date as Дата, is_correct FROM user_stats WHERE user_id = :user_id"),
                session.bind,
                params={"user_id": user_id}
            )

        if not df.empty:
            st.markdown("<h3 style='font-size: 18px; color: #0F172A; margin-top: 25px;'>Активность изучения по дням</h3>", unsafe_allow_html=True)
            df_grouped = df.groupby("Дата").count()
            st.line_chart(df_grouped["is_correct"])
    else:
        st.info("ℹ️ Вы еще не ответили ни на один вопрос в тренажере. Ваша аналитическая панель заполнится после первого раунда!")


def main() -> None:
    # Настройка страницы (строго первая команда Streamlit)
    st.set_page_config(page_title="EnglishCard", page_icon="🇬🇧", layout="wide")

    # Инициализация сессий
    init_session_states()

    # Барьер авторизации
    if not st.session_state.logged_in:
        log.info("Анонимный пользователь открыл приложение. Перенаправление на барьер авторизации.")
        run_authentication(next_question)

    user_id: int = st.session_state.user_info["id"]
    user_name: str = st.session_state.user_info["username"]

    # Отрисовка профиля в Sidebar (новый)
    with st.sidebar:
        st.header("👤 Профиль")
        st.success(f"Вы вошли как: **{user_name}**")
        if st.button("Выйти", type="secondary"):
            log.info(f"Пользователь '{user_name}' (ID: {user_id}) вышел из системы.")
            reset_session_logout()
            st.rerun()

        if st.session_state.answer_status == "correct":
            st.divider()
            st.success("✅ Правильно! Молодец!")
            trigger_confetti()
            play_success_sound()
        elif st.session_state.answer_status == "incorrect":
            st.error("❌ Неверно. Попробуй заново!")

    st.title("🚀 EnglishCard - Изучай английский с удовольствием!")

    if st.session_state.current_word is None:
        next_question()

    # Декларация вкладок интерфейса
    tab_learn, tab_add, tab_delete, tab_stats = st.tabs([
        "📖 Изучение",
        "➕ Добавить слово",
        "🗑️ Удалить слово",
        "📈 Статистика"
    ])

    # Распределение изолированных функций по вкладкам согласно схеме
    with tab_learn:
        lern_func(user_id)

    with tab_add:
        add_word_func(user_id)

    with tab_delete:
        delete_word_func(user_id)

    with tab_stats:
        stats_func(user_id)


if __name__ == '__main__':
    main()
