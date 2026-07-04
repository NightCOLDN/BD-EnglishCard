import streamlit as st
from database.queries import authenticate_user, register_user

def run_authentication(next_question_callback):
    """Экран авторизации с автоматическим очищением полей через st.form.

    При успешном входе вызывает переданную функцию-колбэк next_question_callback
    для генерации первой карточки со словами.
    """
    st.title("🔑 Авторизация в EnglishCard")
    auth_tab1, auth_tab2 = st.tabs(["🔓 Вход", "📝 Регистрация"])

    with auth_tab1:
        st.subheader("Войти в существующий аккаунт")
        with st.form(key="login_form", clear_on_submit=True):
            login_user = st.text_input("Имя пользователя:")
            login_pass = st.text_input("Пароль:", type="password")
            login_submit = st.form_submit_button("Войти", type="primary")

        if login_submit:
            user = authenticate_user(login_user, login_pass)
            if user:
                st.session_state.logged_in = True
                st.session_state.user_info = user
                next_question_callback()  # Генерируем первое слово через колбэк
                st.success("Успешный вход!")
                st.rerun()
            else:
                st.error("Неверное имя пользователя или пароль.")

    with auth_tab2:
        st.subheader("Создать новый аккаунт")
        with st.form(key="register_form", clear_on_submit=True):
            reg_user = st.text_input("Придумайте имя пользователя:")
            reg_pass = st.text_input("Придумайте пароль:", type="password")
            register_submit = st.form_submit_button("Зарегистрироваться")

        if register_submit:
            if reg_user and reg_pass:
                if register_user(reg_user, reg_pass):
                    st.success("Аккаунт успешно создан! Теперь вы можете войти.")
                else:
                    st.error("Это имя пользователя уже занято.")
            else:
                st.warning("Пожалуйста, заполните все поля.")
    st.stop()
