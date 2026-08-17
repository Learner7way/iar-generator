#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
МАСТЕР-СКРИПТ ДЛЯ ПОЛНОГО ЦИКЛА РАБОТЫ
=======================================
Последовательный запуск скриптов с передачей пути к проекту.

Использование: python py_master.py C:\\Projects\\example [--pause]
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import time
import socket
import shutil

# Константы для работы с файлами
HISTORY_DIR = "history"  # Папка для хранения истории
TASK_FILE = "task.txt"   # Файл для сохранения текста задачи

def pause_if_needed():
    """Функция паузы, срабатывает только при наличии аргумента --pause"""
    if '--pause' in sys.argv:
        print("\n" + "="*60)
        input("🔄 НАЖМИТЕ ENTER ДЛЯ ПРОДОЛЖЕНИЯ...")
        print("="*60)

def save_task_to_file(task_text):
    """Сохраняет текст задачи в отдельный файл task.txt"""
    if not task_text.strip():
        return
    
    print(f"\n[СОХРАНЕНИЕ ЗАДАЧИ В ФАЙЛ]")
    print("-" * 40)
    
    try:
        task_path = Path(TASK_FILE)
        with open(task_path, 'w', encoding='utf-8') as f:
            f.write(task_text)
        print(f"  [OK] Задача сохранена в {TASK_FILE} ({len(task_text)} символов)")
    except Exception as e:
        print(f"  [ERROR] Ошибка сохранения задачи: {e}")

def save_py_out_history():
    """Сохраняет копию py_out.md в папку history с датой и временем"""
    print(f"\n[СОХРАНЕНИЕ ИСТОРИИ py_out.md]")
    print("-" * 40)
    
    py_out_path = Path("py_out.md")
    if not py_out_path.exists():
        print(f"  [WARN] Файл py_out.md не найден")
        return
    
    try:
        # Создаем папку history, если её нет
        history_dir = Path(HISTORY_DIR)
        history_dir.mkdir(exist_ok=True)
        
        # Формируем имя файла с датой и временем
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        history_filename = f"py_out_{timestamp}.md"
        history_path = history_dir / history_filename
        
        # Копируем файл
        shutil.copy2(py_out_path, history_path)
        
        # Получаем размер файла
        size = py_out_path.stat().st_size
        size_str = f"{size} байт" if size < 1024 else f"{size/1024:.2f} КБ"
        
        print(f"  [OK] Сохранена копия: {history_filename}")
        print(f"  [OK] Размер: {size_str}")
        print(f"  [OK] Путь: {history_path.absolute()}")
        
    except Exception as e:
        print(f"  [ERROR] Ошибка сохранения истории: {e}")

def clean_output_files():
    """Очищает файлы py_out.md и py_in.txt перед началом работы"""
    print("\n[ОЧИСТКА ФАЙЛОВ]")
    print("-" * 40)
    
    files_to_clean = ["py_out.md", "py_in.txt", "py_in_simplified.txt"]
    cleaned = []
    
    for filename in files_to_clean:
        file_path = Path(filename)
        if file_path.exists():
            try:
                if file_path.stat().st_size > 0:
                    backup_name = f"{filename}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    file_path.rename(backup_name)
                    print(f"  • {filename} -> переименован в {backup_name}")
                else:
                    file_path.unlink()
                    print(f"  • {filename} -> удален")
                cleaned.append(filename)
            except Exception as e:
                print(f"  • ОШИБКА при обработке {filename}: {e}")
        else:
            print(f"  • {filename} -> не найден")
    
    for filename in files_to_clean:
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("")
            print(f"  • {filename} -> создан пустой файл")
        except Exception as e:
            print(f"  • ОШИБКА при создании {filename}: {e}")
    
    if cleaned:
        print(f"\nOK: Очищено {len(cleaned)} файлов")
    else:
        print("\nOK: Все файлы уже чистые")
    
    return True

def check_chrome_debug_port(port=9222, timeout=10):
    """Проверяет доступность порта отладки Chrome"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            if result == 0:
                return True
        except:
            pass
        time.sleep(1)
    return False

def run_script(script_name, args, step_num, step_desc, optional=False):
    """
    Запускает Python скрипт с переданными аргументами.
    Возвращает True если успешно, False если ошибка.
    optional=True - не останавливает мастер-скрипт при ошибке
    """
    cmd = [sys.executable, script_name] + args
    
    print(f"\n{'='*60}")
    print(f"ШАГ {step_num}: {step_desc}")
    print(f"Команда: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    # Пауза перед каждым шагом, если запрошено
    pause_if_needed()
    
    # Устанавливаем переменные окружения для корректной кодировки
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
            encoding='utf-8',
            errors='replace'
        )
        
        for line in process.stdout:
            # Заменяем проблемные символы
            line = line.replace('\U0001f504', '[PROCESS]')
            print(line, end='')
        
        returncode = process.wait()
        
        if returncode == 0:
            print(f"\n[OK] ШАГ {step_num} выполнен успешно")
            return True
        else:
            print(f"\n[ERROR] ШАГ {step_num} завершился с ошибкой (код: {returncode})")
            if optional:
                print(f"[WARN] Продолжаем выполнение (опциональный шаг)")
                return True
            return False
            
    except Exception as e:
        print(f"\n[ERROR] Ошибка при выполнении ШАГА {step_num}: {e}")
        if optional:
            print(f"[WARN] Продолжаем выполнение (опциональный шаг)")
            return True
        return False

def add_task_to_py_out(task_text, py_out_path):
    """Добавляет текст задачи в py_out.md"""
    print(f"\n[ДОБАВЛЕНИЕ ТЕКСТА ЗАДАЧИ]")
    print("-" * 40)
    
    separator = "\n4. Структура проекта и код:"
    
    try:
        with open(py_out_path, 'a', encoding='utf-8') as f:
            f.write(task_text)
            f.write(separator)
            f.write("\n")
        print(f"  [OK] Текст задачи добавлен ({len(task_text)} символов)")
        return True
    except Exception as e:
        print(f"  [ERROR] Ошибка добавления текста задачи: {e}")
        return False

def get_task_from_user():
    """Получает текст задачи от пользователя"""
    print("\n" + "="*60)
    print("ВВОД ТЕКСТА ЗАДАЧИ")
    print("="*60)
    print("Введите текст задачи (для завершения оставьте пустую строку):")
    print("-" * 60)
    
    lines = []
    while True:
        try:
            line = input()
        except UnicodeDecodeError:
            line = input().encode('utf-8', errors='replace').decode('utf-8')
        
        if not line and lines:
            break
        if not line and not lines:
            break
        lines.append(line)
    
    task_text = "\n".join(lines)
    print(f"\n[OK] Получено {len(lines)} строк, {len(task_text)} символов")
    return task_text

def show_file_sizes():
    """Показывает размеры файлов после выполнения"""
    print("\n[РАЗМЕРЫ ФАЙЛОВ]")
    print("-" * 40)
    
    files_to_check = ["py_out.md", "py_in.txt", "py_in_simplified.txt", TASK_FILE]
    
    for filename in files_to_check:
        file_path = Path(filename)
        if file_path.exists():
            size = file_path.stat().st_size
            if size < 1024:
                print(f"  • {filename}: {size} байт")
            elif size < 1024*1024:
                print(f"  • {filename}: {size/1024:.2f} КБ")
            else:
                print(f"  • {filename}: {size/1024/1024:.2f} МБ")
        else:
            print(f"  • {filename}: не найден")

def fix_script_encoding(script_path):
    """Создает временную версию скрипта без эмодзи"""
    if not script_path.exists():
        return script_path
    
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Заменяем эмодзи на текстовые маркеры
        content = content.replace('\U0001f504', '[PROCESS]')
        content = content.replace('✅', '[OK]')
        content = content.replace('❌', '[ERROR]')
        content = content.replace('⚠️', '[WARN]')
        content = content.replace('🔹', '[STEP]')
        content = content.replace('📁', '[DIR]')
        content = content.replace('📝', '[TEXT]')
        content = content.replace('🔄', '[WAIT]')
        
        # Создаем временный файл
        temp_path = script_path.with_suffix('.tmp.py')
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return temp_path
    except:
        return script_path

def main():
    if len(sys.argv) < 2:
        print("Использование: python py_master.py <путь_к_проекту> [--pause]")
        print("Пример: python py_master.py \"C:\\Projects\\example\" --pause")
        sys.exit(1)
    
    # Получаем путь к проекту из аргументов (первый аргумент)
    project_path = sys.argv[1]
    
    # Преобразуем в абсолютный путь и нормализуем
    project_path = str(Path(project_path).absolute())
    
    start_time = datetime.now()
    
    # Определяем пути к скриптам
    script_dir = Path(__file__).parent
    script_add_prompt = script_dir / "add_prompt_to_py_out.py"
    script_iar_xml = script_dir / "pyIAR_xmlValue.py"
    script_ai_data = script_dir / "pyAIData.py"
    script_start_chrome = script_dir / "start_chrome_debug.py"
    script_ai_qesion = script_dir / "pyAIqesion.py"
    script_formatter = script_dir / "py_in_formatter.py"
    script_updater = script_dir / "py_in_updater.py"
    script_iar_generator = script_dir / "iar_generator" / "master.py"
    
    # Путь к py_out.md
    py_out_path = script_dir / "py_out.md"
    
    # Проверяем существование скриптов
    scripts_ok = True
    required_scripts = [
        (script_add_prompt, "add_prompt_to_py_out.py"),
        (script_iar_xml, "pyIAR_xmlValue.py"),
        (script_ai_data, "pyAIData.py"),
        (script_ai_qesion, "pyAIqesion.py"),
        (script_formatter, "py_in_formatter.py"),
        (script_updater, "py_in_updater.py"),
    ]
    
    optional_scripts = [
        (script_start_chrome, "start_chrome_debug.py"),
        (script_iar_generator, "iar_generator/master.py"),
    ]
    
    print("\n" + "="*60)
    print("МАСТЕР-СКРИПТ ДЛЯ ПОЛНОГО ЦИКЛА")
    print("="*60)
    print(f"Проект:          {project_path}")
    print(f"Дата и время:    {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python:          {sys.executable}")
    print(f"Режим паузы:     {'ВКЛЮЧЕН' if '--pause' in sys.argv else 'ВЫКЛЮЧЕН'}")
    print("="*60)
    
    # Пауза перед началом, если запрошено
    pause_if_needed()
    
    # Проверка обязательных скриптов
    print("\n[ПРОВЕРКА СКРИПТОВ]")
    print("-" * 40)
    
    for script_path, script_name in required_scripts:
        if not script_path.exists():
            print(f"  [ERROR] Обязательный скрипт не найден: {script_name}")
            scripts_ok = False
        else:
            print(f"  [OK] {script_name}")
    
    if not scripts_ok:
        print("\n[ERROR] Отсутствуют обязательные скрипты")
        sys.exit(1)
    
    # Информация об опциональных скриптах
    for script_path, script_name in optional_scripts:
        if not script_path.exists():
            print(f"  [WARN] Опциональный скрипт не найден: {script_name}")
        else:
            print(f"  [OK] {script_name}")
    
    # ШАГ 0: Очистка файлов
    if not clean_output_files():
        print("\n[ERROR] Ошибка при очистке файлов")
        sys.exit(1)
    
    # ШАГ 1: Запускаем add_prompt_to_py_out.py
    if script_add_prompt.exists():
        success1 = run_script(
            str(script_add_prompt), 
            [], 
            1, 
            "Добавление содержимого promt.md в py_out.md"
        )
        
        if not success1:
            print("\n[ERROR] Остановка: add_prompt_to_py_out.py завершился с ошибкой")
            sys.exit(1)
    else:
        print("\n[WARN] Пропускаем шаг 1 (скрипт не найден)")
    
    # ШАГ 2: Получаем текст задачи от пользователя
    print("\n" + "="*60)
    print("ШАГ 2: Ввод текста задачи от пользователя")
    print("="*60)
    
    task_text = get_task_from_user()
    
    if task_text.strip():
        # Сохраняем задачу в отдельный файл
        save_task_to_file(task_text)
        
        # Добавляем задачу в py_out.md
        if not add_task_to_py_out(task_text, py_out_path):
            print("\n[ERROR] Ошибка при добавлении текста задачи")
            sys.exit(1)
    else:
        print("\n[INFO] Пустой текст задачи, пропускаем добавление")
    
    # ШАГ 3: Запускаем pyIAR_xmlValue.py с путем к проекту
    success3 = run_script(
        str(script_iar_xml), 
        [project_path], 
        3, 
        "Сбор информации из .ewp файлов (пути, дефайны, линкер)"
    )
    
    if not success3:
        print("\n[ERROR] Остановка: pyIAR_xmlValue.py завершился с ошибкой")
        sys.exit(1)
    
    # ШАГ 4: Запускаем pyAIData.py с путем к проекту
    iar_path = Path(project_path) / "iar"
    script4_args = ["project", str(iar_path)]
    
    success4 = run_script(
        str(script_ai_data), 
        script4_args, 
        4, 
        "Генерация Markdown с содержимым исходных файлов"
    )
    
    if not success4:
        print("\n[ERROR] Остановка: pyAIData.py завершился с ошибкой")
        sys.exit(1)
    
    # ШАГ 5: Запускаем start_chrome_debug.py (опционально)
    if script_start_chrome.exists():
        # Создаем временную версию без эмодзи
        temp_script = fix_script_encoding(script_start_chrome)
        
        run_script(
            str(temp_script),
            [], 
            5,
            "Запуск Chrome в режиме отладки",
            optional=True
        )
        
        # Удаляем временный файл
        if temp_script != script_start_chrome:
            try:
                temp_script.unlink()
            except:
                pass
        
        print("\n[WAIT] Ожидание запуска Chrome (10 секунд)...")
        time.sleep(10)
        
        # Проверяем доступность порта отладки
        if check_chrome_debug_port():
            print("[OK] Chrome доступен для подключения")
        else:
            print("[WARN] Chrome не отвечает на порту 9222")
    else:
        print("\n[ШАГ 5] Пропускаем (start_chrome_debug.py не найден)")
    
    # ШАГ 6: Запускаем pyAIqesion.py
    # Проверяем доступность Chrome перед запуском
    if check_chrome_debug_port(timeout=5):
        # Создаем временную версию без эмодзи
        temp_script = fix_script_encoding(script_ai_qesion)
        
        success6 = run_script(
            str(temp_script),
            [],
            6,
            "Отправка вопроса в DeepSeek и получение ответа"
        )
        
        # Удаляем временный файл
        if temp_script != script_ai_qesion:
            try:
                temp_script.unlink()
            except:
                pass
    else:
        print("\n[WARN] Chrome не доступен, пропускаем ШАГ 6")
        success6 = False
    
    if not success6:
        print("\n[WARN] ШАГ 6 завершился с ошибкой, но продолжаем")
    
    # ШАГ 7: Запускаем py_in_formatter.py
    if script_formatter.exists():
        # Создаем временную версию без эмодзи
        temp_script = fix_script_encoding(script_formatter)
        
        success7 = run_script(
            str(temp_script),
            [],
            7,
            "Форматирование ответа (упрощение)",
            optional=True
        )
        
        # Удаляем временный файл
        if temp_script != script_formatter:
            try:
                temp_script.unlink()
            except:
                pass
    else:
        print("\n[ШАГ 7] Пропускаем (py_in_formatter.py не найден)")
    
    # ШАГ 8: Запускаем py_in_updater.py с путем к проекту
    if script_updater.exists():
        # Создаем временную версию без эмодзи
        temp_script = fix_script_encoding(script_updater)
        
        success8 = run_script(
            str(temp_script),
            [project_path],
            8,
            "Выполнение действий по упрощенному ответу",
            optional=True
        )
        
        # Удаляем временный файл
        if temp_script != script_updater:
            try:
                temp_script.unlink()
            except:
                pass
    else:
        print("\n[ШАГ 8] Пропускаем (py_in_updater.py не найден)")
    
    # ШАГ 9: Запускаем iar_generator/master.py с путем к проекту
    if script_iar_generator.exists():
        # Создаем временную версию без эмодзи
        temp_script = fix_script_encoding(script_iar_generator)
        
        success9 = run_script(
            str(temp_script),
            ["generate", project_path, "project"],
            9,
            "Замена проектных файлов IAR",
            optional=True
        )
        
        # Удаляем временный файл
        if temp_script != script_iar_generator:
            try:
                temp_script.unlink()
            except:
                pass
    else:
        print("\n[ШАГ 9] Пропускаем (iar_generator/master.py не найден)")
    
    # Сохраняем копию py_out.md в историю
    save_py_out_history()
    
    # Показываем размеры файлов
    show_file_sizes()
    
    # Финальный отчет
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "="*60)
    print("ВСЕ ОПЕРАЦИИ ЗАВЕРШЕНЫ")
    print("="*60)
    print(f"Проект:          {project_path}")
    print(f"Начало:          {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Окончание:       {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Длительность:    {duration:.2f} сек")
    print(f"Входной файл:    {Path.cwd() / 'py_out.md'}")
    print(f"Выходной файл:   {Path.cwd() / 'py_in.txt'}")
    print(f"Упрощенный:      {Path.cwd() / 'py_in_simplified.txt'}")
    print(f"Файл задачи:     {Path.cwd() / TASK_FILE}")
    print(f"Папка истории:   {Path.cwd() / HISTORY_DIR}")
    print("="*60)

if __name__ == "__main__":
    main()