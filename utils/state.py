# utils/state.py
import streamlit as st

def init_session_states():
    """Декларация всех переменных состояний приложения в Streamlit Session State."""
    states = {
        "logged_in": False,
        "user_info": None,
        "current_word": None,
        "options": [],
        "answer_status": None,
        "used_words": [],
        "round_question_count": 0,
        "round_correct_count": 0,
        "round_finished": False,
        "current_word_fault": False
    }
    for key, val in states.items():
        if key not in st.session_state:
            st.session_state[key] = val


def reset_session_logout():
    """Полная очистка состояния сессии при выходе пользователя из аккаунта."""
    st.session_state.logged_in = False
    st.session_state.user_info = None
    st.session_state.current_word = None
    st.session_state.options = []
    st.session_state.answer_status = None
