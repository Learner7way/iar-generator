#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для запуска Chrome в режиме отладки (debug mode)
Порт: 9222
Профиль: C:\temp\chrome_debug
Сайт: https://chat.deepseek.com
"""

import subprocess
import os
import sys
import socket
import time
import requests
import json
from pathlib import Path

def check_port(port):
    """Проверяет, свободен ли порт"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result != 0  # True если порт свободен

def check_browser_connected(port):
    """Проверяет, отвечает ли браузер на запросы отладки"""
    try:
        response = requests.get(f"http://localhost:{port}/json/version", timeout=2)
        if response.status_code == 200:
            data = response.json()
            return True, data.get('Browser', 'Unknown')
    except:
        pass
    return False, None

def get_open_tabs(port):
    """Получает список открытых вкладок"""
    try:
        response = requests.get(f"http://localhost:{port}/json/list", timeout=2)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return []

def check_deepseek_page(port):
    """Проверяет, открыта ли страница DeepSeek"""
    tabs = get_open_tabs(port)
    if not tabs:
        return False, None
    
    for tab in tabs:
        url = tab.get('url', '')
        title = tab.get('title', '')
        if 'deepseek.com' in url:
            return True, url
        if 'DeepSeek' in title:
            return True, url
    
    return False, None

def find_chrome():
    """Ищет установленный Chrome"""
    possible_paths = [
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        os.path.expanduser("~\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe")
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None

def wait_for_browser(port, timeout=30):
    """Ожидает запуска браузера"""
    print(f"  Ожидание запуска браузера (макс. {timeout}с)...")
    
    for i in range(timeout):
        connected, browser_info = check_browser_connected(port)
        if connected:
            print(f"  [OK] Браузер запущен ({browser_info})")
            return True
        if i % 5 == 0 and i > 0:
            print(f"  ... {i}с")
        time.sleep(1)
    
    print("  [FAIL] Браузер не отвечает")
    return False

def main():
    print("=" * 50)
    print("Chrome Debug Mode Launcher")
    print("=" * 50)
    print()
    
    # Ищем Chrome
    print("[1/7] Поиск Chrome...")
    chrome_path = find_chrome()
    if not chrome_path:
        print("  [FAIL] Chrome не найден!")
        print("  Установите Chrome или проверьте путь.")
        input("\nНажмите Enter для выхода...")
        return
    
    print(f"  [OK] Chrome найден: {chrome_path}")
    
    # Папка для профиля
    print("\n[2/7] Настройка профиля...")
    profile_dir = "C:\\temp\\chrome_debug"
    try:
        os.makedirs(profile_dir, exist_ok=True)
        print(f"  [OK] Папка профиля: {profile_dir}")
    except Exception as e:
        print(f"  [FAIL] Ошибка создания папки: {e}")
        input("\nНажмите Enter для выхода...")
        return
    
    # Проверяем порт и запущен ли уже браузер
    print("\n[3/7] Проверка порта...")
    port = 9222
    
    # Проверяем, может браузер уже запущен
    browser_running, browser_info = check_browser_connected(port)
    
    if browser_running:
        print(f"  [INFO] Браузер уже запущен ({browser_info})")
        
        # Проверяем, открыта ли страница DeepSeek
        deepseek_open, deepseek_url = check_deepseek_page(port)
        if deepseek_open:
            print(f"  [OK] Страница DeepSeek уже открыта: {deepseek_url}")
            print("\n  Можно сразу запускать pyAIqesion.py")
        else:
            print("  [WARN] Страница DeepSeek не открыта")
            print("  Откройте https://chat.deepseek.com в браузере")
        
        print("\n[4/7] Пропускаем запуск (браузер уже работает)")
        
    else:
        # Проверяем, свободен ли порт
        if not check_port(port):
            print(f"  [WARN] Порт {port} занят, но браузер не отвечает")
            print("  Возможно, другой процесс использует порт")
            
            choice = input("  Принудительно запустить? (y/n): ").lower().strip()
            if choice != 'y':
                print("  [INFO] Отменено пользователем")
                input("\nНажмите Enter для выхода...")
                return
        else:
            print(f"  [OK] Порт {port} свободен")
        
        # Запускаем Chrome
        print("\n[4/7] Запуск Chrome...")
        cmd = [
            chrome_path,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "https://chat.deepseek.com"
        ]
        
        print(f"  • Порт: {port}")
        print(f"  • Профиль: {profile_dir}")
        print(f"  • Сайт: https://chat.deepseek.com")
        
        try:
            # Запускаем Chrome
            subprocess.Popen(cmd)
            print("  [OK] Команда запуска отправлена")
            
        except Exception as e:
            print(f"  [FAIL] Ошибка запуска: {e}")
            input("\nНажмите Enter для выхода...")
            return
        
        # Ожидаем запуска
        print("\n[5/7] Ожидание запуска...")
        if not wait_for_browser(port, 30):
            print("  [FAIL] Браузер не запустился")
            input("\nНажмите Enter для выхода...")
            return
        
        # Проверяем, открылась ли страница
        print("\n[6/7] Проверка страницы...")
        time.sleep(3)  # Даем время на загрузку
        
        deepseek_open, deepseek_url = check_deepseek_page(port)
        if deepseek_open:
            print(f"  [OK] Страница DeepSeek открыта: {deepseek_url}")
        else:
            print("  [WARN] Страница DeepSeek не обнаружена")
            print("  Откройте https://chat.deepseek.com вручную")
    
    # Финальная информация
    print("\n[7/7] Проверка готовности...")
    
    # Финальная проверка перед выходом
    browser_running, browser_info = check_browser_connected(port)
    if not browser_running:
        print("  [FAIL] Браузер не отвечает!")
        input("\nНажмите Enter для выхода...")
        return
    
    deepseek_open, deepseek_url = check_deepseek_page(port)
    
    print("\n" + "=" * 50)
    print("ГОТОВО")
    print("=" * 50)
    print()
    print("Статус:")
    print(f"  • Браузер: {browser_info}")
    print(f"  • Порт: {port}")
    if deepseek_open:
        print(f"  • DeepSeek: ОТКРЫТ ({deepseek_url})")
    else:
        print(f"  • DeepSeek: НЕ ОТКРЫТ (откройте вручную)")
    print(f"  • Профиль: {profile_dir}")
    print()
    print("Инструкция:")
    print("  1. Если DeepSeek не открыт - откройте https://chat.deepseek.com")
    print("  2. Войдите в аккаунт (если требуется)")
    print("  3. Запустите pyAIqesion.py")
    print()
    print("=" * 50)
    
    input("Нажмите Enter для выхода...")

if __name__ == "__main__":
    main()