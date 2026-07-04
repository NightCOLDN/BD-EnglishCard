# utils/effects.py
import base64
import streamlit as st
import streamlit.components.v1 as components
from config import SUCCESS_SOUND_FILE

def trigger_confetti():
    """Запускает визуальный эффект конфетти на экране через JS-скрипт Canvas-Confetti."""
    confetti_js = """
    <script src="https://jsdelivr.net"></script>
    <script>
    function launch() {
        const target = window.parent.confetti ? window.parent.confetti : confetti;
        target({ particleCount: 150, spread: 80, origin: { y: 0.6 }, zIndex: 9999 });
    }
    launch();
    </script>
    """
    components.html(confetti_js, height=1, width=1)


def play_success_sound():
    """Воспроизводит аудиофайл победы, кодируя его в base64."""
    try:
        with open(SUCCESS_SOUND_FILE, "rb") as f:
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
