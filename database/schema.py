DATABASE_SCHEMA_TEXT = """
 +-----------------------------------+

 |               USERS               | <-- Пользователи системы
 +-----------------------------------+

 | id (PK) : SERIAL                  |
 | username : VARCHAR(50)            |
 | password_hash : VARCHAR(255)      |
 +-----------------------------------+

        |                 |
     (1 : N)           (1 : N)
        v                 v
 +-----------------+ +-----------------------------------+

 |   USER_STATS    | |         USER_CUSTOM_WORDS         | <-- Личные слова пользователя
 +-----------------+ +-----------------------------------+

 | id (PK) : SERIAL| | id (PK) : SERIAL                  |
 | user_id (FK)    | | user_id (FK) : INT REFERENCES     |
 |   REFERENCES ---+ |   USERS(id) ON DELETE CASCADE     |
 |   USERS(id)     | | word_en : VARCHAR(100)            |
 | is_correct: BOOL| | word_ru : VARCHAR(100)            |
 | answered_at:TS  | +-----------------------------------+
 +-----------------+                      |
                                       (1 : N)
                                          v
 +-----------------------------------+ +-----------------------------------+

 |        USER_DELETED_WORDS         | |           GLOBAL_WORDS            | <-- Базовые слова
 +-----------------------------------+ +-----------------------------------+

 | id (PK) : SERIAL                  | | id (PK) : SERIAL                  |
 | user_id (FK) : INT REFERENCES ----+ | word_en : VARCHAR(100)            |
 |   USERS(id) ON DELETE CASCADE     | | word_ru : VARCHAR(100)            |
 | global_word_id(FK): INTEGER ------->|                                   |
 +-----------------------------------+ +-----------------------------------+
"""
