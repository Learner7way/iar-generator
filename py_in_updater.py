#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для применения изменений из py_in.txt к файлам проекта с использованием Git.

Поддерживает:
- Обновление существующих файлов
- Создание новых файлов
- Удаление файлов
- Автоматическое управление версиями с инкрементом

Использование: python py_in_updater.py <путь_к_проекту>
Пример: python py_in_updater.py "C:\\Projects\\example"
"""

import sys
import re
import subprocess
from pathlib import Path
from datetime import datetime
import json

from core.config import default_config as cfg
from utils.file_reader import read_text


class VersionManager:
    """Класс для управления версиями в Git репозитории."""

    def __init__(self, repo_path):
        self.repo_path = repo_path
        self.version_file = repo_path / ".version.json"
        self.current_version = self._load_version()

    def _load_version(self):
        """Загрузка текущей версии из файла."""
        if self.version_file.exists():
            try:
                with open(self.version_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("version", 1)
            except Exception:
                return 1
        return 1

    def _save_version(self):
        """Сохранение текущей версии в файл."""
        try:
            with open(self.version_file, "w", encoding="utf-8") as f:
                json.dump({"version": self.current_version}, f, indent=2)
            return True
        except Exception:
            return False

    def get_next_version(self):
        """Получение следующей версии (инкремент)."""
        return self.current_version + 1

    def increment_version(self):
        """Инкремент версии и сохранение."""
        self.current_version += 1
        self._save_version()
        return self.current_version


def parse_py_in_file(file_path):
    """
    Парсинг py_in.txt файла с поддержкой разных форматов.
    Поддерживает:
    - Формат с блоками "Файл:" и ```c содержимое```
    - Формат с секцией "Содержимое файлов:"
    - Формат со списком create/update в начале
    """
    print(f"\n[*] Reading file: {file_path}")

    if not file_path.exists():
        print(f"[-] File not found: {file_path}")
        return None, None

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    print(f"[*] File size: {len(content)} bytes")

    files_to_update = {}
    files_to_delete = []

    # Проверяем наличие секции "Содержимое файлов:"
    if "Содержимое файлов:" in content:
        print("[*] Found 'Содержимое файлов:' section")
        files_section = content.split("Содержимое файлов:")[1]

        # Различные паттерны для поиска файлов
        file_patterns = [
            r"\*\*Файл:\*\*\s*`([^`]+)`\s*```c\n(.*?)```",
            r"\*\*Файл:\*\*\s*([^\n]+?)\s*```c\n(.*?)```",
            r"Файл:\s*`([^`]+)`\s*```c\n(.*?)```",
            r"Файл:\s*([^\n]+?)\s*```c\n(.*?)```",
        ]

        for pattern in file_patterns:
            matches = re.findall(pattern, files_section, re.DOTALL)
            for file_path, file_content in matches:
                file_path = file_path.strip().strip("`").strip()
                if file_path not in files_to_update:
                    files_to_update[file_path] = file_content.strip()
                    print(f"   [[DOC]] File to process: {file_path}")

    else:
        print("[*] Using flexible format detection")
        # Разбиваем содержимое на секции по маркеру "Файл:"
        sections = re.split(r"(?=Файл:)", content)

        for section in sections:
            if not section.strip():
                continue

            # Ищем путь к файлу
            file_path_match = re.search(r"Файл:\s*`([^`]+)`", section)
            if not file_path_match:
                file_path_match = re.search(r"Файл:\s*([^\n]+)", section)

            if file_path_match:
                file_path = file_path_match.group(1).strip()

                # Проверяем, не помечен ли файл как удаленный
                if any(
                    word in section.lower() for word in ["удален", "removed", "deleted"]
                ):
                    if file_path not in files_to_delete:
                        files_to_delete.append(file_path)
                        print(f"   [⌫] File marked for deletion: {file_path}")
                    continue

                # Ищем содержимое файла в markdown блоке ```c ... ```
                content_match = re.search(r"```c\n(.*?)```", section, re.DOTALL)
                if content_match:
                    file_content = content_match.group(1).strip()
                    files_to_update[file_path] = file_content
                    print(f"   [[DOC]] File to process: {file_path}")

    # Ищем файлы в верхней части (create/update/delete)
    header_section = (
        content.split("Содержимое файлов:")[0]
        if "Содержимое файлов:" in content
        else content
    )

    # Паттерны для поиска операций
    operation_patterns = [
        # create/update файлов
        (r"(?:create|update)\s+`([^`]+)`", "create/update"),
        # удаление файлов
        (r"(?:delete|remove|удален)\s+`([^`]+)`", "delete"),
        # маркированный список
        (r"[•*]\s*`([^`]+)`\s*\(([^)]+)\)", "list_with_status"),
        (r"[•*]\s*`([^`]+)`", "list_simple"),
    ]

    for pattern, pattern_type in operation_patterns:
        matches = re.findall(pattern, header_section)
        for match in matches:
            if pattern_type == "list_with_status":
                file_path, status = match
                file_path = file_path.strip()
                status_lower = status.lower()

                if any(
                    word in status_lower for word in ["удален", "removed", "deleted"]
                ):
                    if (
                        file_path not in files_to_delete
                        and file_path not in files_to_update
                    ):
                        files_to_delete.append(file_path)
                        print(f"   [⌫] File marked for deletion (in list): {file_path}")

                elif any(word in status_lower for word in ["создан", "new", "created"]):
                    if file_path not in files_to_update:
                        # Проверяем, есть ли содержимое для этого файла
                        found = False
                        for existing_path in files_to_update.keys():
                            if file_path in existing_path:
                                found = True
                                break

                        if not found:
                            print(
                                f"   [[WARN]] File marked as created but not found in content: {file_path}"
                            )

            elif pattern_type == "list_simple":
                file_path = (
                    match.strip() if isinstance(match, str) else match[0].strip()
                )
                if (
                    file_path not in files_to_update
                    and file_path not in files_to_delete
                    and not any(file_path in f for f in files_to_update.keys())
                ):
                    print(f"   [i] File mentioned in list: {file_path}")

            else:  # create/update или delete
                file_path = (
                    match.strip() if isinstance(match, str) else match[0].strip()
                )

                if pattern_type == "delete":
                    if (
                        file_path not in files_to_delete
                        and file_path not in files_to_update
                    ):
                        files_to_delete.append(file_path)
                        print(
                            f"   [⌫] File marked for deletion (explicit): {file_path}"
                        )
                else:  # create/update
                    if file_path not in files_to_update:
                        # Проверяем, есть ли содержимое для этого файла где-то в файле
                        found = False
                        # Ищем в секциях с содержимым
                        if "Содержимое файлов:" in content:
                            files_section = content.split("Содержимое файлов:")[1]
                            for pattern in file_patterns:
                                content_matches = re.findall(
                                    pattern, files_section, re.DOTALL
                                )
                                for f_path, f_content in content_matches:
                                    if f_path.strip().strip("`").strip() == file_path:
                                        files_to_update[file_path] = f_content.strip()
                                        print(
                                            f"   [[DOC]] Found content for listed file: {file_path}"
                                        )
                                        found = True
                                        break
                                if found:
                                    break
                        else:
                            # Ищем в любом месте файла
                            for section in sections:
                                if file_path in section and "```c" in section:
                                    content_match = re.search(
                                        r"```c\n(.*?)```", section, re.DOTALL
                                    )
                                    if content_match:
                                        files_to_update[file_path] = (
                                            content_match.group(1).strip()
                                        )
                                        print(
                                            f"   [[DOC]] Found content for listed file: {file_path}"
                                        )
                                        found = True
                                        break

                        if not found:
                            print(
                                f"   [[WARN]] File listed for update but no content found: {file_path}"
                            )

    # Удаляем дубликаты
    files_to_update = {
        k: v for k, v in files_to_update.items() if k not in files_to_delete
    }
    files_to_delete = list(set(files_to_delete))

    print(f"[+] Files to update/create: {len(files_to_update)}")
    print(f"[+] Files to delete: {len(files_to_delete)}")

    if files_to_update:
        print("[+] Files to update:")
        for f in files_to_update.keys():
            print(f"      - {f}")

    if files_to_delete:
        print("[+] Files to delete:")
        for f in files_to_delete:
            print(f"      - {f}")

    return files_to_update, files_to_delete


def ensure_directory_exists(file_path):
    """
    Создание директории для файла, если она не существует.
    """
    directory = file_path.parent
    if not directory.exists():
        try:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"   [[OK]] Created directory: {directory}")
            return True
        except Exception as e:
            print(f"   [!] Error creating directory {directory}: {e}")
            return False
    return True


def run_git_command(repo_path, cmd):
    """
    Выполнение Git команды в репозитории.
    """
    try:
        process = subprocess.run(
            cmd, cwd=repo_path, capture_output=True, text=True, encoding="utf-8"
        )
        return process.returncode == 0, process.stdout, process.stderr
    except Exception as e:
        return False, "", str(e)


def check_git_repository(repo_path):
    """
    Проверка наличия Git репозитория.
    """
    git_dir = repo_path / ".git"
    if not git_dir.exists():
        print(f"\n[WARN]  Directory is not a Git repository: {repo_path}")
        response = input("   Initialize Git repository? (y/N): ")
        if response.lower() == "y":
            success, out, err = run_git_command(repo_path, ["git", "init"])
            if success:
                print("   [[OK]] Git repository initialized")
                return True
            else:
                print(f"   [!] Error initializing Git: {err}")
                return False
        return False
    return True


def git_commit_changes(repo_path, message_prefix, version_info=None):
    """
    Создание Git коммита с информацией о версии.
    """
    # Проверяем статус
    success, out, err = run_git_command(repo_path, ["git", "status", "--porcelain"])
    if not success:
        print(f"   [!] Error checking status: {err}")
        return False, None

    if not out.strip():
        print("   [i] No changes to commit")
        return True, None

    # Добавляем все изменения
    print("   [Git] Adding files...")
    success, out, err = run_git_command(repo_path, ["git", "add", "-A"])
    if not success:
        print(f"   [!] Error in git add: {err}")
        return False, None

    # Формируем сообщение коммита
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if version_info:
        version_num = version_info.get("number", "?")
        commit_message = f"{message_prefix} [version {version_num}] [{timestamp}]"
    else:
        commit_message = f"{message_prefix} [{timestamp}]"

    print("   [Git] Creating commit...")
    success, out, err = run_git_command(
        repo_path, ["git", "commit", "-m", commit_message]
    )

    if success:
        print(f"   [[OK]] Commit created: {commit_message}")
        # Получаем хеш коммита
        success, out, err = run_git_command(
            repo_path, ["git", "rev-parse", "--short", "HEAD"]
        )
        commit_hash = out.strip() if success else "unknown"
        print(f"   [Git] Commit hash: {commit_hash}")
        return True, commit_hash
    else:
        print(f"   [!] Error creating commit: {err}")
        return False, None


def delete_file(file_path, base_dir):
    """
    Удаление файла.
    """
    full_path = base_dir / file_path

    print(f"\n[⌫] Deleting: {file_path}")

    if not full_path.exists():
        print("   [i] File already doesn't exist, skipping")
        return True, "skipped"

    if not full_path.is_file():
        print(f"   [!] Not a file (maybe directory): {full_path}")
        # Пытаемся удалить как директорию
        try:
            import shutil

            shutil.rmtree(full_path)
            print(f"   [[OK]] Directory deleted: {full_path}")
            return True, "deleted"
        except Exception as e:
            print(f"   [!] Error deleting directory: {e}")
            return False, "failed"

    try:
        file_size = full_path.stat().st_size
        full_path.unlink()
        print(f"   [[OK]] File deleted (size: {file_size} bytes)")

        # Проверяем, нужно ли удалить пустую директорию
        parent_dir = full_path.parent
        if parent_dir.exists() and not any(parent_dir.iterdir()):
            try:
                parent_dir.rmdir()
                print(f"   [[OK]] Deleted empty directory: {parent_dir}")
            except Exception:
                pass

        return True, "deleted"
    except Exception as e:
        print(f"   [!] Error deleting file: {e}")
        return False, "failed"


def update_file(file_path, new_content, base_dir):
    """
    Обновление файла новым содержимым.
    Создаёт недостающие директории при необходимости.
    Возвращает: (success, status) где status = 'created', 'updated', 'skipped', 'failed'
    """
    full_path = base_dir / file_path

    print(f"\n[+] Processing: {file_path}")

    # Создаём директории, если нужно
    if not ensure_directory_exists(full_path):
        return False, "failed"

    # Проверяем, существует ли файл
    is_new_file = not full_path.exists()

    # Для новых файлов
    if is_new_file:
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print("   [[OK]] Created new file")
            return True, "created"
        except Exception as e:
            print(f"   [!] Error creating file: {e}")
            return False, "failed"

    # Для существующих файлов проверяем изменения
    old_content, read_error = read_text(full_path)
    if old_content is None:
        print(f"   [!] Error reading file: {read_error}")
        return False, "failed"

    # Если содержимое совпадает, пропускаем
    if old_content.strip() == new_content.strip():
        print("   [=] Content unchanged, skipping")
        return True, "skipped"

    # Записываем новое содержимое
    try:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("   [[OK]] File updated")
        return True, "updated"
    except Exception as e:
        print(f"   [!] Error writing file: {e}")
        return False, "failed"


def print_summary(results, base_dir, start_time, git_commits, version_info=None):
    """
    Вывод сводки по обновлениям.
    """
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print("\n" + "=" * 60)
    print("OPERATION SUMMARY")
    print("=" * 60)
    print(f"Base directory: {base_dir}")
    print(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duration: {duration:.2f} sec")
    print("-" * 60)

    if version_info:
        print(
            f"Version: {version_info.get('current', 'N/A')} → {version_info.get('after', 'N/A')}"
        )
        print("-" * 60)

    updated = []
    skipped = []
    failed = []
    created = []
    deleted = []
    delete_failed = []
    delete_skipped = []

    for file_path, status in results.get("files", {}).items():
        if status == "updated":
            updated.append(file_path)
        elif status == "skipped":
            skipped.append(file_path)
        elif status == "failed":
            failed.append(file_path)
        elif status == "created":
            created.append(file_path)

    for file_path, status in results.get("deleted", {}).items():
        if status == "deleted":
            deleted.append(file_path)
        elif status == "skipped":
            delete_skipped.append(file_path)
        elif status == "failed":
            delete_failed.append(file_path)

    print("\n[DATA] Statistics:")
    print(f"   - New files created: {len(created)}")
    print(f"   - Files updated: {len(updated)}")
    print(f"   - Files deleted: {len(deleted)}")
    print(f"   - Skipped (unchanged): {len(skipped)}")
    print(f"   - Delete skipped (not exist): {len(delete_skipped)}")
    print(f"   - Update errors: {len(failed)}")
    print(f"   - Delete errors: {len(delete_failed)}")

    if git_commits:
        print("\n[FIX] Git operations:")
        if git_commits.get("before"):
            print(f"   - Commit before changes: {git_commits['before']}")
        if git_commits.get("after"):
            print(f"   - Commit after changes: {git_commits['after']}")

    if created:
        print("\n🆕 Created files:")
        for f in created:
            print(f"   + {f}")

    if updated:
        print("\n[NOTE] Updated files:")
        for f in updated:
            print(f"   [OK] {f}")

    if deleted:
        print("\n[DEL]  Deleted files:")
        for f in deleted:
            print(f"   ⌫ {f}")

    if skipped:
        print("\n⏭  Skipped files (unchanged):")
        for f in skipped:
            print(f"   = {f}")

    if delete_skipped:
        print("\n⏭  Delete skipped (already gone):")
        for f in delete_skipped:
            print(f"   = {f}")

    if failed:
        print("\n[ERROR] Files with update errors:")
        for f in failed:
            print(f"   [ERROR] {f}")

    if delete_failed:
        print("\n[ERROR] Files with delete errors:")
        for f in delete_failed:
            print(f"   [ERROR] {f}")

    print("=" * 60)


def confirm_plan(files_to_update, files_to_delete, base_dir, version_info):
    """
    Отображение плана и запрос подтверждения.
    """
    print("\n[LIST] Operation plan:")

    if files_to_update:
        print(f"\n   [NOTE] Files to update/create ({len(files_to_update)}):")
        for file_path in sorted(files_to_update.keys()):
            full_path = base_dir / file_path
            if full_path.exists():
                print(f"      - {file_path} (exists)")
            else:
                print(f"      + {file_path} (will be created)")

    if files_to_delete:
        print(f"\n   [DEL]  Files to delete ({len(files_to_delete)}):")
        for file_path in sorted(files_to_delete):
            full_path = base_dir / file_path
            if full_path.exists():
                print(f"      ⌫ {file_path} (exists)")
            else:
                print(f"      ⌫ {file_path} (already doesn't exist)")

    if version_info:
        print("\n[PIN] Version information:")
        print(f"   - Current version: {version_info['current']}")
        print(f"   - Next version: {version_info['next']}")

    print("\n[WARN]  Changes will be committed to Git with version increment")
    response = input("\nProceed with operations? (y/N): ")

    return response.lower() == "y"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    project_path = sys.argv[1]
    base_dir = Path(project_path).resolve()

    if not base_dir.exists():
        print(f"[ERROR] Base directory does not exist: {base_dir}")
        response = input("Create directory? (y/N): ")
        if response.lower() == "y":
            try:
                base_dir.mkdir(parents=True, exist_ok=True)
                print(f"[OK] Directory created: {base_dir}")
            except Exception as e:
                print(f"[ERROR] Error creating directory: {e}")
                sys.exit(1)
        else:
            sys.exit(1)

    # Путь к py_in.txt из конфигурации конвейера
    py_in_path = cfg.answer_file

    print("=" * 60)
    print("[PROCESS] FILE UPDATER FROM py_in.txt (with Git versioning)")
    print("=" * 60)
    print(f"[DIR] Project base directory: {base_dir}")
    print(f"[DOC] Input file: {py_in_path}")

    start_time = datetime.now()
    git_commits = {}
    version_info = {}

    # Проверяем Git репозиторий
    use_git = check_git_repository(base_dir)
    if not use_git:
        print("\n[WARN]  Continuing without Git")
        response = input("Continue? (y/N): ")
        if response.lower() != "y":
            sys.exit(0)

    # Инициализируем менеджер версий
    version_mgr = VersionManager(base_dir) if use_git else None

    # Парсим py_in.txt
    files_to_update, files_to_delete = parse_py_in_file(py_in_path)

    if not files_to_update and not files_to_delete:
        print("[-] No operations to perform")
        sys.exit(0)

    # Подготавливаем информацию о версиях
    if use_git:
        current_version = version_mgr.current_version
        next_version = version_mgr.get_next_version()
        version_info = {
            "current": f"v{current_version}",
            "next": f"v{next_version}",
            "current_num": current_version,
            "next_num": next_version,
        }

    # Показываем план и запрашиваем подтверждение
    if not confirm_plan(files_to_update, files_to_delete, base_dir, version_info):
        print("\n[-] Operation cancelled")
        sys.exit(0)

    # Создаем коммит перед изменениями
    if use_git:
        print("\n[Git] Creating pre-update commit...")
        success, commit_hash = git_commit_changes(
            base_dir,
            "Temporary version before update",
            {"number": version_info["current_num"]},
        )
        if success and commit_hash:
            git_commits["before"] = commit_hash

    # Применяем изменения
    results = {"files": {}, "deleted": {}}

    # Сначала удаляем файлы
    if files_to_delete:
        print(f"\n{'='*60}")
        print("[DEL]  DELETING FILES")
        print(f"{'='*60}")

        for file_path in files_to_delete:
            success, status = delete_file(file_path, base_dir)
            results["deleted"][file_path] = status

    # Затем обновляем/создаем файлы
    if files_to_update:
        print(f"\n{'='*60}")
        print("[NOTE] UPDATING/CREATING FILES")
        print(f"{'='*60}")

        for file_path, new_content in files_to_update.items():
            success, status = update_file(file_path, new_content, base_dir)
            results["files"][file_path] = status

    # Создаем коммит после изменений с инкрементом версии
    if use_git:
        has_changes = any(
            status in ["created", "updated"] for status in results["files"].values()
        ) or any(status == "deleted" for status in results["deleted"].values())

        if has_changes:
            new_version = version_mgr.increment_version()
            version_info["after"] = f"v{new_version}"

            print(f"\n[Git] Creating post-update commit (version {new_version})...")
            success_count = sum(
                1
                for status in results["files"].values()
                if status in ["created", "updated"]
            ) + sum(1 for status in results["deleted"].values() if status == "deleted")
            success, commit_hash = git_commit_changes(
                base_dir,
                f"Update {success_count} files from py_in.txt",
                {"number": new_version},
            )
            if success and commit_hash:
                git_commits["after"] = commit_hash
        else:
            version_info["after"] = version_info["current"]

    # Выводим сводку
    print_summary(results, base_dir, start_time, git_commits, version_info)


if __name__ == "__main__":
    main()
