from openai import OpenAI
import requests
import time
import pyperclip
import os
from dotenv import load_dotenv

load_dotenv()  

client = OpenAI(
  base_url=os.getenv("PROVIDER"),
  api_key=os.getenv("API_KEY"),
)
prompt = """
Найди мне в электронном письме код верификации, тайное слово или ссылку для проверки почты. 
Не пиши лишнего текста и форматирования. 
В твоем ответе должен быть ТОЛЬКО код верификации или тайное слово или полная ссылка на верификацию!


"""




BASE_URL = "https://api.guerrillamail.com/ajax.php"

def get_email_address():
    params = {
        "f": "get_email_address",
        "lang": "en",
        "agent": "PythonScript/1.0"
    }
    r = requests.get(BASE_URL, params=params)
    r.raise_for_status()
    return r.json(), r.cookies

def get_email_list(sid_token, cookies):
    params = {
        "f": "get_email_list",
        "offset": 0,
        "sid_token": sid_token,
        "agent": "PythonScript/1.0"
    }
    r = requests.get(BASE_URL, params=params, cookies=cookies)
    r.raise_for_status()
    return r.json()

def fetch_email(sid_token, mail_id, cookies):
    params = {
        "f": "fetch_email",
        "email_id": mail_id,
        "sid_token": sid_token,
        "agent": "PythonScript/1.0"
    }
    r = requests.get(BASE_URL, params=params, cookies=cookies)
    r.raise_for_status()
    return r.json()

def main():
    # 1. Создаём почту
    data, cookies = get_email_address()
    email = data.get("email_addr")
    sid_token = data.get("sid_token")
    print(f"[+] Создан email: {email}")
    
    # Копируем email в буфер обмена
    pyperclip.copy(email)
    print("[+] Email скопирован в буфер обмена")

    # 2. Ожидаем письма
    print("[*] Ожидаем входящие письма...")
    while True:
        time.sleep(5)  # каждые 5 секунд проверяем
        inbox = get_email_list(sid_token, cookies)
        messages = inbox.get("list", [])
        if messages and len(messages) > 1:
            print(f"\n[+] Найдено {len(messages)-1} письмо(писем)")
            mail_id = messages[0].get("mail_id")
            subject = messages[0].get("mail_subject")
            sender = messages[0].get("mail_from")
            print(f"--- Письмо ---\nТема: {subject}")
            # Получаем содержимое
            mail = fetch_email(sid_token, mail_id, cookies)
            body = mail.get("mail_body", "")
            print(f"[*] Обработка...")
            
            completion = client.chat.completions.create(
                model=os.getenv("MODEL"),
                messages=[{
                        "role": 'user',
                        "content": prompt + body
                    }],
                stream=False
            )
            return completion.choices[0].message.content
        else:
            print("[ ] Пока писем нет...")

if __name__ == "__main__":
    code = main()
    print(code)
    
    # Копируем код верификации в буфер обмена
    pyperclip.copy(code.strip())
    print("[+] Код верификации скопирован в буфер обмена")
    
    input("Нажмите Enter для выхода...")


