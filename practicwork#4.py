import threading
import json
import time
from datetime import datetime
import hashlib
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_PATH = os.path.join(SCRIPT_DIR, "users.json")
TIMERS_PATH = os.path.join(SCRIPT_DIR, "timers.json")
LOG_PATH = os.path.join(SCRIPT_DIR, "app.log")
LICENSE_PATH = os.path.join(SCRIPT_DIR, "license.key")

users_lock = threading.Lock()
timers_lock = threading.Lock()
log_lock = threading.Lock()

class Logger:
    def __init__(self):
        self.log_queue = []
        self.running = True
        self.thread = threading.Thread(target=self._write_logs)
        self.thread.start()

    def log(self, level, username, message):
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        log_entry = f"[{level}] [{timestamp}] [{username}] -- {message}\n"
        with log_lock:
            self.log_queue.append(log_entry)

    def _write_logs(self):
        while self.running or self.log_queue:
            if self.log_queue:
                with log_lock:
                    entry = self.log_queue.pop(0)
                with open(LOG_PATH, "a") as f:
                    f.write(entry)
            time.sleep(0.1)

    def stop(self):
        self.running = False
        self.thread.join()

logger = Logger()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register(username, password):
    with users_lock:
        if os.path.exists(USERS_PATH):
            with open(USERS_PATH, "r") as f:
                users = json.load(f)
        else:
            users = {}
        if username in users:
            return False
        users[username] = hash_password(password)
        with open(USERS_PATH, "w") as f:
            json.dump(users, f)
        logger.log("INFO", username, "User registered")
        return True

def login(username, password):
    if not os.path.exists(USERS_PATH):
        return False
    with users_lock:
        with open(USERS_PATH, "r") as f:
            users = json.load(f)
    if username in users and users[username] == hash_password(password):
        logger.log("INFO", username, "User logged in")
        return True
    return False

class TimerManager:
    def __init__(self):
        self.timers = []
        self.save_thread = threading.Thread(target=self._save_timers)
        self.save_thread.start()

    def add_timer(self, username, seconds, message):
        timer = {
            "username": username,
            "end_time": time.time() + seconds,
            "message": message
        }
        self.timers.append(timer)
        threading.Thread(target=self._run_timer, args=(timer,)).start()
        logger.log("INFO", username, f"Timer set: {message} ({seconds}s)")

    def _run_timer(self, timer):
        while time.time() < timer["end_time"]:
            time.sleep(1)
        print(f"\nНапоминание: {timer['message']}")
        logger.log("INFO", timer["username"], f"Timer triggered: {timer['message']}")

    def _save_timers(self):
        while True:
            time.sleep(5)
            with timers_lock:
                with open(TIMERS_PATH, "w") as f:
                    json.dump(self.timers, f)

class LicenseChecker:
    def __init__(self):
        self.license_key = None
        self.start_time = time.time()
        self.thread = threading.Thread(target=self._check_license)
        self.thread.start()

    def _check_license(self):
        while True:
            if os.path.exists(LICENSE_PATH):
                with open(LICENSE_PATH, "r") as f:
                    self.license_key = f.read().strip()
                print("Лицензия активна")
                break
            else:
                elapsed = time.time() - self.start_time
                if elapsed > 1800: 
                    print("Пробная лицензия завершена!")
                    os._exit(0)
                time.sleep(60)

def main():
    if not os.path.exists(USERS_PATH):
        with open(USERS_PATH, "w") as f:
            json.dump({}, f)
    if not os.path.exists(TIMERS_PATH):
        with open(TIMERS_PATH, "w") as f:
            json.dump([], f)
    
    license_checker = LicenseChecker()
    timer_manager = TimerManager()
    current_user = None

    while True:
        if not current_user:
            action = input("1. Регистрация\n2. Вход\nВыберите действие: ")
            if action == "1":
                username = input("Логин: ")
                password = input("Пароль: ")
                if register(username, password):
                    print("Успешная регистрация!")
                else:
                    print("Ошибка регистрации!")
            elif action == "2":
                username = input("Логин: ")
                password = input("Пароль: ")
                if login(username, password):
                    current_user = username
                    print("Успешный вход!")
                else:
                    print("Ошибка входа!")
        else:
            action = input("1. Установить таймер\n2. Выход\nВыберите действие: ")
            if action == "1":
                try:
                    seconds = int(input("Время (секунды): "))
                    message = input("Сообщение: ")
                    timer_manager.add_timer(current_user, seconds, message)
                except Exception as e:
                    logger.log("ERROR", current_user, f"Ошибка таймера: {str(e)}")
            elif action == "2":
                current_user = None

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.stop()