from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import time
import os
import pyperclip

INPUT_FILE = "py_out.md"
OUTPUT_FILE = "py_in.txt"

def connect_to_existing_chrome():
    """Подключается к уже запущенному Chrome с отладкой"""
    print("\n[ПОДКЛЮЧЕНИЕ К БРАУЗЕРУ]")
    print("-" * 40)
    
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("OK: Подключено к Chrome")
        return driver
    except Exception as e:
        print(f"ОШИБКА: {e}")
        return None

def read_question():
    """Читает вопрос из файла"""
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        example = "Напиши приветствие"
        with open(INPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(example)
        print(f"OK: Создан файл {INPUT_FILE}")
        return example

def find_input_field(driver):
    """Находит поле ввода"""
    print("\n[ПОИСК ПОЛЯ ВВОДА]")
    print("-" * 40)
    
    try:
        textarea = driver.find_element(By.TAG_NAME, 'textarea')
        if textarea:
            print("OK: Поле ввода найдено")
            return textarea
    except:
        pass
    
    try:
        editable = driver.find_element(By.CSS_SELECTOR, "[contenteditable='true']")
        if editable:
            print("OK: Поле ввода найдено")
            return editable
    except:
        pass
    
    print("ОШИБКА: Поле ввода не найдено")
    return None

def paste_text(driver, input_field, text):
    """Вставляет текст через буфер обмена"""
    print("\n[ВСТАВКА ТЕКСТА]")
    print("-" * 40)
    
    pyperclip.copy(text)
    print("OK: Текст скопирован")
    
    input_field.click()
    time.sleep(0.5)
    input_field.clear()
    time.sleep(0.5)
    
    action = ActionChains(driver)
    action.key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
    print("OK: Текст вставлен")
    
    return True

def send_question(driver, input_field):
    """Отправляет вопрос с секундной паузой"""
    print("\n[ОТПРАВКА]")
    print("-" * 40)
    
    print("Пауза 1 секунда перед отправкой...")
    time.sleep(1)
    
    input_field.send_keys(Keys.RETURN)
    print("OK: Вопрос отправлен")
    
    return True

def check_for_continue_button(driver):
    """Проверяет наличие кнопки продолжения и нажимает её"""
    continue_selectors = [
        "//button[contains(text(), 'Continue')]",
        "//button[contains(text(), 'Продолжить')]",
        "//button[contains(text(), 'Generate more')]",
        "//button[contains(text(), 'Сгенерировать ещё')]",
        "//button[contains(@class, 'continue')]",
        "//button[contains(@class, 'generate-more')]",
        ".continue-btn",
        ".generate-more-btn",
        "//div[contains(@class, 'continue')]//button",
        "//span[contains(text(), 'Continue')]/ancestor::button"
    ]
    
    for selector in continue_selectors:
        try:
            if selector.startswith("//"):
                buttons = driver.find_elements(By.XPATH, selector)
            else:
                buttons = driver.find_elements(By.CSS_SELECTOR, selector)
            
            for button in buttons:
                if button and button.is_displayed() and button.is_enabled():
                    # Подсвечиваем кнопку для отладки
                    driver.execute_script("arguments[0].style.border='3px solid orange'", button)
                    print(f"\n  🔘 Найдена кнопка: {button.text[:30]}")
                    return button
        except:
            continue
    
    return None

def get_answer(driver):
    """Получает ответ, следя за последним сообщением и кнопкой продолжения"""
    print("\n[ПОЛУЧЕНИЕ ОТВЕТА]")
    print("-" * 40)
    
    print("Ожидание ответа...")
    
    # Запоминаем текущее количество сообщений
    try:
        prev_messages = driver.find_elements(By.CSS_SELECTOR, 
            ".assistant-message, .message-assistant, [class*='assistant'], .ds-markdown")
        prev_count = len(prev_messages)
    except:
        prev_count = 0
    
    max_wait = 300  # 5 минут
    stable_required = 5
    no_change_count = 0
    last_length = 0
    last_message = None
    last_update_time = time.time()
    last_log_time = time.time()
    continue_clicked = False
    
    for second in range(max_wait):
        try:
            # ПРОВЕРКА КНОПКИ ПРОДОЛЖЕНИЯ (каждые 2 секунды)
            if second % 2 == 0 and not continue_clicked:
                continue_btn = check_for_continue_button(driver)
                if continue_btn:
                    print(f"\n  🔘 Нажимаю кнопку продолжения...")
                    try:
                        continue_btn.click()
                        print(f"  ✓ Кнопка нажата, жду продолжения...")
                        continue_clicked = True
                        no_change_count = 0
                        last_update_time = time.time()
                        time.sleep(2)  # Даем время на реакцию
                        continue
                    except Exception as e:
                        print(f"  ✗ Ошибка нажатия: {e}")
            
            # Получаем все сообщения ассистента
            all_messages = driver.find_elements(By.CSS_SELECTOR, 
                ".assistant-message, .message-assistant, [class*='assistant'], .ds-markdown, .markdown-body")
            
            current_count = len(all_messages)
            
            # Если появилось новое сообщение
            if current_count > prev_count:
                print(f"\n[NEW] Новое сообщение! (всего {current_count})")
                prev_count = current_count
                last_message = all_messages[-1]
                last_length = len(last_message.text)
                last_update_time = time.time()
                print(f"  • Начальный размер: {last_length} символов")
                no_change_count = 0
                continue_clicked = False  # Сбрасываем флаг для нового сообщения
            
            # Если есть последнее сообщение, следим за его ростом
            elif last_message:
                try:
                    current_text = last_message.text
                    current_length = len(current_text)
                    
                    if current_length > last_length:
                        growth = current_length - last_length
                        # Логируем только значительные изменения
                        if growth > 100 or time.time() - last_log_time > 10:
                            print(f"  • Рост: +{growth} (всего {current_length})")
                            last_log_time = time.time()
                        last_length = current_length
                        no_change_count = 0
                        last_update_time = time.time()
                    elif current_length == last_length and last_length > 0:
                        no_change_count += 1
                        
                        # Показываем статус каждые 2 секунды без изменений
                        if no_change_count % 2 == 0:
                            stable_time = int(time.time() - last_update_time)
                            print(f"  • Стабильно {current_length} ({stable_time}с)")
                        
                        # Если стабильно достаточно долго - завершаем
                        if no_change_count >= stable_required and not continue_btn:
                            print(f"\nOK: Ответ получен! ({current_length} символов)")
                            return current_text
                except:
                    # Если элемент устарел, пробуем найти последнее сообщение заново
                    if all_messages:
                        last_message = all_messages[-1]
                    else:
                        last_message = None
            
            # Если нет нового сообщения
            else:
                if second % 20 == 0:
                    print(f"  • Ожидание... ({second}с)")
            
            time.sleep(1)
            
        except Exception as e:
            if second % 10 == 0:
                print(f"  • Проверка... ({second}с)")
            time.sleep(1)
    
    # Таймаут - пробуем получить последнее сообщение
    try:
        all_messages = driver.find_elements(By.CSS_SELECTOR, 
            ".assistant-message, .message-assistant, [class*='assistant']")
        if all_messages:
            last_text = all_messages[-1].text
            if last_text:
                print(f"\nWARN: Таймаут {max_wait}с, но получен ответ ({len(last_text)} символов)")
                return last_text
    except:
        pass
    
    print("\nОШИБКА: Ответ не получен")
    return None

def save_answer(text):
    """Сохраняет ответ в файл"""
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"OK: Ответ сохранен в {OUTPUT_FILE}")
        return True
    except Exception as e:
        print(f"ОШИБКА сохранения: {e}")
        return False

def main():
    print("=" * 50)
    print("DeepSeek Assistant")
    print("=" * 50)
    
    driver = connect_to_existing_chrome()
    if not driver:
        return
    
    if "deepseek.com" not in driver.current_url:
        driver.get('https://chat.deepseek.com/')
        time.sleep(3)
    
    question = read_question()
    if not question:
        driver.quit()
        return
    
    print(f"\n[QUESTION] {question[:100]}{'...' if len(question) > 100 else ''}")
    
    input_field = find_input_field(driver)
    if not input_field:
        driver.quit()
        return
    
    paste_text(driver, input_field, question)
    send_question(driver, input_field)
    
    answer = get_answer(driver)
    
    if answer:
        print(f"\n[RESULT] Получено {len(answer)} символов")
        save_answer(answer)
        print(f"\n[PREVIEW]\n{answer[:300]}...")
    else:
        print("\n[ERROR] Не удалось получить ответ")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()