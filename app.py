import streamlit as st
import random
import base64
import streamlit.components.v1 as components
import pandas as pd
from database.connection import get_db_engine
from sqlalchemy import text
from database.connection import init_db
from database.queries import (
    get_available_words,
    generate_quiz_options,
    add_custom_word,
    delete_word_for_user,
    authenticate_user,
    register_user,
    log_user_answer,
    get_user_statistics,
    get_user_words_count
)

# Настройка страницы (обязательно первой строчкой)
st.set_page_config(page_title="EnglishCard", page_icon="📚", layout="wide")

# Автоматическая проверка и создание всех таблиц при старте приложения
init_db()

# ==============================================================================
# БЛОК ЭФФЕКТОВ (АНИМАЦИЯ И ЗВУК)
# ==============================================================================
def trigger_confetti():
    """Запускает анимацию конфетти на экране через JS-скрипт Canvas-Confetti."""
    confetti_js = """
    <script src="https://jsdelivr.net"></script>
    <script>
        function launch() {
            const target = window.parent.confetti ? window.parent.confetti : confetti;
            target({
                particleCount: 150,
                spread: 80,
                origin: { y: 0.6 },
                zIndex: 9999
            });
        }
        launch();
    </script>
    """
    components.html(confetti_js, height=1, width=1)

def play_success_sound():
    try:
        with open("win.mp3", "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            audio_html = f"""
                <audio autoplay style="display:none;">
                    <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                </audio>
            """
            st.markdown(audio_html, unsafe_allow_html=True)
    except FileNotFoundError:
        pass  # Если файла нет, приложение продолжит работу без звука

# ==============================================================================
# ИНИЦИАЛИЗАЦИЯ СОСТОЯНИЙ СЕССИИ (SESSION STATE)
# ==============================================================================
QUESTIONS_PER_ROUND = 10

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_info" not in st.session_state:
    st.session_state.user_info = None
if "current_word" not in st.session_state:
    st.session_state.current_word = None
if "options" not in st.session_state:
    st.session_state.options = []
if "answer_status" not in st.session_state:
    st.session_state.answer_status = None
if "used_words" not in st.session_state: # Список для хранения ID недавно показанных слов
    st.session_state.used_words = []
#  Переменные для ограничения раунда обучения
if "round_question_count" not in st.session_state:
    st.session_state.round_question_count = 0  # Сколько слов показано в этом раунде
if "round_correct_count" not in st.session_state:
    st.session_state.round_correct_count = 0   # Сколько правильных ответов дано за раунд
if "round_finished" not in st.session_state:
    st.session_state.round_finished = False    # Завершен ли текущий раунд

# Был ли ошибочный ответ на текущее слово
if "current_word_fault" not in st.session_state:
    st.session_state.current_word_fault = False

def next_question():
    """Выбирает случайное слово, учитывая лимиты текущего раунда."""
    if st.session_state.user_info:
        # Проверяем, не достигнут ли лимит раунда
        if st.session_state.round_question_count >= QUESTIONS_PER_ROUND:
            st.session_state.round_finished = True
            st.session_state.current_word = None
            return

        user_id = st.session_state.user_info["id"]
        all_words = get_available_words(user_id)

        if not all_words:   # ЗАЩИТА: Если в базе вообще нет слов (все удалены или еще не добавлены)
            st.session_state.current_word = None
            st.session_state.options = []
            st.session_state.answer_status = None
            return

        # Фильтрация повторений
        fresh_words = [w for w in all_words if w["id"] not in st.session_state.used_words]
        if not fresh_words:
            st.session_state.used_words = []
            fresh_words = all_words

        # ЗАЩИТА: Дополнительная проверка перед выбором
        if fresh_words:
            selected_word = random.choice(fresh_words)
            st.session_state.used_words.append(selected_word["id"])

            if len(st.session_state.used_words) > min(5, len(all_words) - 1):
                st.session_state.used_words.pop(0)

            st.session_state.round_question_count += 1
            st.session_state.current_word = selected_word
            st.session_state.options = generate_quiz_options(user_id, selected_word)
            st.session_state.answer_status = None
            st.session_state.current_word_fault = False
        else:
            st.session_state.current_word = None

        selected_word = random.choice(fresh_words)
        st.session_state.used_words.append(selected_word["id"])

        if len(st.session_state.used_words) > min(5, len(all_words) - 1):
            st.session_state.used_words.pop(0)

        # Увеличиваем счетчик вопросов в раунде
        st.session_state.round_question_count += 1

        st.session_state.current_word = selected_word
        st.session_state.options = generate_quiz_options(user_id, selected_word)
        st.session_state.answer_status = None

        # Новое слово начинается без ошибок!
        st.session_state.current_word_fault = False

# ==============================================================================
# ЭКРАН АВТОРИЗАЦИИ И РЕГИСТРАЦИИ (Блокирует интерфейс для гостей)
# ==============================================================================
if not st.session_state.logged_in:
    st.title("🔐 Авторизация в EnglishCard")

    auth_tab1, auth_tab2 = st.tabs(["🔑 Вход", "📝 Регистрация"])

    with auth_tab1:
        st.subheader("Войти в существующий аккаунт")
        login_user = st.text_input("Имя пользователя:", key="login_username")
        login_pass = st.text_input("Пароль:", type="password", key="login_password")

        if st.button("Войти", type="primary", key="btn_login_submit"):
            user = authenticate_user(login_user, login_pass)
            if user:
                st.session_state.logged_in = True
                st.session_state.user_info = user
                next_question()  # Генерируем первое слово
                st.success("Успешный вход!")
                st.rerun()
            else:
                st.error("Неверное имя пользователя или пароль.")

    with auth_tab2:
        st.subheader("Создать новый аккаунт")
        reg_user = st.text_input("Придумайте имя пользователя:", key="reg_username")
        reg_pass = st.text_input("Придумайте пароль:", type="password", key="reg_password")

        if st.button("Зарегистрироваться", key="btn_register_submit"):
            if reg_user and reg_pass:
                if register_user(reg_user, reg_pass):
                    st.success("Аккаунт успешно создан! Теперь вы можете войти на соседней вкладке.")
                else:
                    st.error("Это имя пользователя уже занято.")
            else:
                st.warning("Пожалуйста, заполните все поля.")

    st.stop()  # Жесткая остановка. Все, что написано ниже, увидят ТОЛЬКО авторизованные!

# ==============================================================================
# БОКОВАЯ ПАНЕЛЬ (Доступна строго после авторизации)
# ==============================================================================
USER_ID = st.session_state.user_info["id"]
USER_NAME = st.session_state.user_info["username"]

with st.sidebar:
    st.header("👤 Профиль")
    st.success(f"Вы вошли как: **{USER_NAME}**")

    if st.button("Выйти", type="secondary", key="btn_logout_sidebar"):
        st.session_state.logged_in = False
        st.session_state.user_info = None
        st.session_state.current_word = None
        st.session_state.options = []
        st.session_state.answer_status = None
        st.rerun()

# ==============================================================================
# ОСНОВНОЙ ИНТЕРФЕЙС ПРИЛОЖЕНИЯ
# ==============================================================================
st.title("📚 EnglishCard - Изучай английский с удовольствием!")

# Если пользователь вошел, но слово еще не выбрано (например, после удаления последнего слова)
if st.session_state.current_word is None:
    next_question()

tab_learn, tab_add, tab_delete, tab_stats = st.tabs([
    "📖 Изучение",
    "➕ Добавить слово",
    "🗑️ Удалить слово",
    "📊 Статистика"
])

# ------------------------------------------------------------------------------
# ВКЛАДКА 1: ИЗУЧЕНИЕ СЛОВ
# ------------------------------------------------------------------------------

with tab_learn:
    st.header("📖 Изучаем слова")

    # 1. ПРОВЕРКА: Если раунд завершен, выводим экран итогов
    if st.session_state.round_finished:
        st.balloons() # Анимация воздушных шаров в честь окончания урока
        st.success("🎉 Поздравляем! Вы завершили раунд обучения!")

        score_percent = round((st.session_state.round_correct_count / QUESTIONS_PER_ROUND) * 100)

        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.metric(label="Показано слов в раунде", value=QUESTIONS_PER_ROUND)
        with res_col2:
            st.metric(label="Правильных ответов", value=f"{st.session_state.round_correct_count} из {QUESTIONS_PER_ROUND}")

        st.info(f"Ваша точность в этом раунде составила: **{score_percent}%**")

        if st.button("🔄 Начать новый раунд", type="primary", use_container_width=True, key="btn_restart_round"):
            st.session_state.round_question_count = 0
            st.session_state.round_correct_count = 0
            st.session_state.round_finished = False
            next_question()
            st.rerun()

    # 2. Если раунд еще идет и слово выбрано — показываем интерфейс теста
    elif st.session_state.current_word:
        st.caption(f"Прогресс раунда: Вопрос **{st.session_state.round_question_count}** из **{QUESTIONS_PER_ROUND}**")

        col_word, col_status = st.columns(2)
        with col_word:
            st.markdown(f"### Слово: **{st.session_state.current_word['ru'].lower()}**")
            st.markdown("#### Как будет по-английски?")
            st.markdown("##### Выберите перевод: 🔗")

        with col_status:
            if st.session_state.answer_status == "correct":
                st.success("✅ Правильно! Молодец!")
                trigger_confetti()
                play_success_sound()
            elif st.session_state.answer_status == "incorrect":
                st.error("❌ Неверно. Попробуй ответить заново! Попытки не ограничены.")

        # Выводим 4 варианта ответа в одну горизонтальную строку
        cols = st.columns(4)
        for i, option in enumerate(st.session_state.options):
            with cols[i]:
                # Кнопки блокируются СТРОГО только после нахождения правильного ответа
                is_disabled = (st.session_state.answer_status == "correct")

                if st.button(option, key=f"opt_{option}_{i}", use_container_width=True, disabled=is_disabled):
                    if option == st.session_state.current_word["en"]:
                        st.session_state.answer_status = "correct"
                        log_user_answer(USER_ID, True)

                        if not st.session_state.current_word_fault:
                            st.session_state.round_correct_count += 1
                    else:
                        st.session_state.answer_status = "incorrect"
                        log_user_answer(USER_ID, False)
                        # Запоминаем, что пользователь совершил ошибку на этом слове
                        st.session_state.current_word_fault = True
                    st.rerun()

        # Кнопка перехода к следующему слову (выровнена внутри блока elif)
        if st.session_state.answer_status == "correct":
            st.markdown("")
            if st.button("➡️ Следующее слово", use_container_width=True, key="btn_next_word_clean"):
                next_question()
                st.rerun()

    # 3. Кейс, когда слов в базе вообще не осталось (all_words пустой)
    else:
        st.warning("⚠️ В вашем словаре не осталось доступных слов для изучения!")
        st.info("💡 Похоже, вы удалили или скрыли все базовые слова. Чтобы продолжить тренировки, перейдите во вкладку **'➕ Добавить слово'** выше и добавьте свои собственные слова в личный словарь.")

        # Кнопка переключения появляется только при успешном ответе
        if st.session_state.answer_status == "correct":
            st.markdown("")
            if st.button("➡️ Следующее слово", use_container_width=True, key="btn_next_word_clean"):
                next_question()
                st.rerun()

        st.info("В вашем словаре нет доступных слов. Добавьте их во вкладке выше.")

    st.markdown("")
    with st.expander("📂 Посмотреть схему базы данных (Database Schema)"):
        st.write("Ниже представлена физическая реляционная схема базы данных PostgreSQL для данного проекта:")

        # Переносим схему без лишних внутренних табуляций, чтобы Python не выдавал ошибку
        schema_text = """
  +-----------------------------------+

  |               USERS               |  <-- Пользователи системы
  +-----------------------------------+

  | id (PK)           : SERIAL        |
  | username          : VARCHAR(50)   |
  | password_hash     : VARCHAR(255)  |
  +-----------------------------------+

           |                 |
           | (1 : N)         | (1 : N)
           v                 v
  +-----------------+  +-----------------------------------+

  |   USER_STATS    |  |         USER_CUSTOM_WORDS         | <-- Личные слова
  +-----------------+  +-----------------------------------+

  | id (PK) : SERIAL|  | id (PK)           : SERIAL        |
  | user_id : INT   |  | user_id (FK)      : INTEGER       |
  | is_correct: BOOL|  | word_en           : VARCHAR(100)  |
  | answered_at:TS  |  | word_ru           : VARCHAR(100)  |
  +-----------------+  +-----------------------------------+
                             |
                             | (1 : N)
                             v
  +-----------------------------------+      +-----------------------------------+

  |        USER_DELETED_WORDS         |      |           GLOBAL_WORDS            | <-- Базовые слова
  +-----------------------------------+      +-----------------------------------+

  | id (PK)           : SERIAL        |      | id (PK)           : SERIAL        |
  | user_id           : INTEGER       |      | word_en           : VARCHAR(100)  |
  | global_word_id(FK): INTEGER ------------>| word_ru           : VARCHAR(100)  |
  +-----------------------------------+      +-----------------------------------+
        """
        st.code(schema_text, language="text")

# ------------------------------------------------------------------------------
# ВКЛАДКА 2: ДОБАВЛЕНИЕ СЛОВА
# ------------------------------------------------------------------------------
with tab_add:
    st.header("➕ Добавление нового слова в личный словарь")
    new_ru = st.text_input("Слово на русском:", key="add_ru")
    new_en = st.text_input("Перевод на английский:", key="add_en")

    if st.button("Сохранить слово", type="primary"):
        cleaned_ru = new_ru.strip().lower()
        cleaned_en = new_en.strip().lower()

        if not cleaned_ru or not cleaned_en:
            st.warning("Пожалуйста, заполните оба поля.")
        elif not cleaned_en.isascii():
            st.error("Английское слово должно быть написано латинскими буквами!")
        else:
            add_custom_word(USER_ID, cleaned_en, cleaned_ru)
            st.success(f"Слово '{cleaned_en}' успешно добавлено в ваш словарь!")
            next_question()

 # ------------------------------------------------------------------------------
 # ВКЛАДКА 3: УДАЛЕНИЕ СЛОВА
 # ------------------------------------------------------------------------------

with tab_delete:
    st.header("🗑️ Персональное удаление слов")
    if st.session_state.current_word:
        st.write(f"Вы можете удалить текущее слово из своего списка: **{st.session_state.current_word['ru']}**")
        # ИСПРАВЛЕНО: Убедитесь, что здесь тоже уникальный ключ
        if st.button("Удалить текущее слово", type="primary", key="delete_current_word"):
            delete_word_for_user(USER_ID, st.session_state.current_word)
            st.toast("Слово скрыто из вашего словаря!")
            next_question()
            st.rerun()

    else:
        st.write("Нет доступных слов для удаления.")

# ------------------------------------------------------------------------------
# ВКЛАДКА 4: СТАТИСТИКА
# ------------------------------------------------------------------------------

with tab_stats:
    st.header("📊 Ваша статистика обучения")

    # Берем актуальные данные из базы
    stats = get_user_statistics(USER_ID)
    total_words = get_user_words_count(USER_ID)

    # Выводим показатели в виде интерактивных карточек-метрик в один ряд
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1:
        st.metric(label="🎒 Слов в обучении", value=total_words)
    with m_col2:
        st.metric(label="🎯 Верных ответов", value=stats["correct"])
    with m_col3:
        st.metric(label="📈 Точность ответов", value=f"{stats['accuracy']}%")

    st.markdown("---")

    # Защита прогресс-бара: отображаем его только если были ответы
    if stats["total"] > 0:
        st.markdown(f"**Ваш прогресс точности (всего ответов: {stats['total']}):**")
        st.progress(stats["accuracy"] / 100.0)
    else:
        st.info("💡 Вы еще не ответили ни на один вопрос в тренажере. Пройдите тест во вкладке 'Изучение', чтобы здесь появилась статистика!")

    engine = get_db_engine()
    # Извлекаем историю ответов текущего юзера
    df = pd.read_sql(text("SELECT answered_at::date as Дата, is_correct FROM user_stats WHERE user_id = :user_id"), engine, params={"user_id": USER_ID})

    if not df.empty:
        st.markdown("### 📈 Активность изучения по дням")
        # Группируем по дате и считаем количество кликов
        df_grouped = df.groupby("Дата").count()
        st.line_chart(df_grouped["is_correct"])