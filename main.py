# Импорт необходимых библиотек
from openai import OpenAI  # Для работы с AI API (OpenAI-совместимые провайдеры)
import requests  # Для HTTP-запросов к Guerrilla Mail API
import time  # Для паузы между проверками писем
import pyperclip  # Для копирования текста в буфер обмена
import os  # Для работы с переменными окружения
from dotenv import load_dotenv  # Для загрузки конфигурации из .env файла

# Загружаем переменные окружения из файла .env
load_dotenv()

# Инициализируем клиент для работы с AI API
# base_url - адрес API провайдера (OpenRouter, OpenAI и т.д.)
# api_key - ваш секретный ключ для доступа к API
client = OpenAI(
  base_url=os.getenv("PROVIDER"),
  api_key=os.getenv("API_KEY"),
)

# Промпт для AI - инструкция по извлечению кода верификации из письма
# AI должна вернуть только сам код/ссылку без дополнительного текста
prompt = """
Найди мне в электронном письме код верификации, тайное слово или ссылку для проверки почты.
Не пиши лишнего текста и форматирования.
В твоем ответе должен быть ТОЛЬКО код верификации или тайное слово или полная ссылка на верификацию!


"""




# Базовый URL для API Guerrilla Mail - сервиса временных email-адресов
BASE_URL = "https://api.guerrillamail.com/ajax.php"

def get_email_address():
    """
    Создает новый временный email-адрес через Guerrilla Mail API

    Returns:
        tuple: (данные с email и токеном, cookies для последующих запросов)
    """
    # Параметры запроса для создания нового email
    params = {
        "f": "get_email_address",  # Функция API - получить email адрес
        "lang": "en",  # Язык интерфейса
        "agent": "PythonScript/1.0"  # Идентификатор клиента
    }
    # Отправляем GET-запрос к API
    r = requests.get(BASE_URL, params=params)
    r.raise_for_status()  # Проверяем, что запрос успешен (не 4xx или 5xx)
    return r.json(), r.cookies  # Возвращаем JSON-данные и cookies для сессии

def get_email_list(sid_token, cookies):
    """
    Получает список входящих писем для текущей email-сессии

    Args:
        sid_token (str): Токен сессии, полученный при создании email
        cookies: Cookies из предыдущего запроса для поддержания сессии

    Returns:
        dict: JSON с списком писем
    """
    # Параметры для получения списка писем
    params = {
        "f": "get_email_list",  # Функция API - получить список писем
        "offset": 0,  # Смещение (с какого письма начать), 0 = с начала
        "sid_token": sid_token,  # Токен сессии для идентификации почтового ящика
        "agent": "PythonScript/1.0"  # Идентификатор клиента
    }
    # Отправляем запрос с cookies для поддержания сессии
    r = requests.get(BASE_URL, params=params, cookies=cookies)
    r.raise_for_status()  # Проверяем успешность запроса
    return r.json()  # Возвращаем список писем в формате JSON

def fetch_email(sid_token, mail_id, cookies):
    """
    Получает полное содержимое конкретного письма по его ID

    Args:
        sid_token (str): Токен сессии
        mail_id (str/int): ID письма, которое нужно получить
        cookies: Cookies сессии

    Returns:
        dict: JSON с полным содержимым письма (тема, отправитель, тело)
    """
    # Параметры для получения конкретного письма
    params = {
        "f": "fetch_email",  # Функция API - получить содержимое письма
        "email_id": mail_id,  # ID конкретного письма
        "sid_token": sid_token,  # Токен сессии
        "agent": "PythonScript/1.0"  # Идентификатор клиента
    }
    # Запрашиваем полное содержимое письма
    r = requests.get(BASE_URL, params=params, cookies=cookies)
    r.raise_for_status()  # Проверяем успешность запроса
    return r.json()  # Возвращаем данные письма

def main():
    """
    Основная функция программы

    Логика работы:
    1. Создает временный email-адрес
    2. Копирует его в буфер обмена
    3. Ждет входящих писем в бесконечном цикле
    4. Когда письмо приходит - отправляет его AI для извлечения кода
    5. Возвращает найденный код верификации

    Returns:
        str: Код верификации, найденный AI в письме
    """
    # ===== ШАГ 1: Создание временного email-адреса =====
    data, cookies = get_email_address()
    email = data.get("email_addr")  # Извлекаем email из ответа API
    sid_token = data.get("sid_token")  # Извлекаем токен сессии
    print(f"[+] Создан email: {email}")

    # Копируем созданный email в буфер обмена для удобной вставки при регистрации
    pyperclip.copy(email)
    print("[+] Email скопирован в буфер обмена")

    # ===== ШАГ 2: Мониторинг входящих писем =====
    print("[*] Ожидаем входящие письма...")
    while True:
        time.sleep(5)  # Пауза 5 секунд между проверками (чтобы не нагружать API)

        # Получаем список всех писем в почтовом ящике
        inbox = get_email_list(sid_token, cookies)
        messages = inbox.get("list", [])  # Извлекаем список писем

        # Проверяем, пришло ли новое письмо (больше 1, т.к. всегда есть служебное)
        if messages and len(messages) > 1:
            print(f"\n[+] Найдено {len(messages)-1} письмо(писем)")

            # Берем первое (самое свежее) письмо
            mail_id = messages[0].get("mail_id")  # ID письма
            subject = messages[0].get("mail_subject")  # Тема письма
            sender = messages[0].get("mail_from")  # Отправитель
            print(f"--- Письмо ---\nТема: {subject}")

            # ===== ШАГ 3: Получение содержимого письма =====
            mail = fetch_email(sid_token, mail_id, cookies)
            body = mail.get("mail_body", "")  # Извлекаем тело письма (HTML или текст)
            print(f"[*] Обработка...")

            # ===== ШАГ 4: AI-обработка письма для извлечения кода =====
            # Отправляем запрос к AI API с промптом и содержимым письма
            completion = client.chat.completions.create(
                model=os.getenv("MODEL"),  # Используем модель из .env
                messages=[{
                        "role": 'user',  # Роль пользователя
                        "content": prompt + body  # Промпт + содержимое письма
                    }],
                stream=False  # Не используем потоковую передачу
            )
            # Возвращаем ответ AI (должен содержать только код верификации)
            return completion.choices[0].message.content
        else:
            # Если писем еще нет - продолжаем ждать
            print("[ ] Пока писем нет...")

# ===== ТОЧКА ВХОДА В ПРОГРАММУ =====
if __name__ == "__main__":
    # Запускаем основную функцию и получаем код верификации
    code = main()

    # Выводим найденный код на экран
    print(code)

    # Копируем код верификации в буфер обмена для быстрой вставки
    # strip() удаляет лишние пробелы и переносы строк
    pyperclip.copy(code.strip())
    print("[+] Код верификации скопирован в буфер обмена")

    # Ждем нажатия Enter, чтобы окно не закрылось сразу
    # Это дает пользователю время прочитать результат
    input("Нажмите Enter для выхода...")


