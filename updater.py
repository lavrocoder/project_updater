import json
import shutil
import zipfile
from pathlib import Path
from typing import Dict

import requests


class ProjectUpdater:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.version_file = self.project_root / "version.json"
        self.update_dir = self.project_root / ".update"
        self.backup_dir = self.project_root / ".backup"

    def load_version_info(self) -> Dict:
        """Загрузка информации о текущей версии"""
        with open(self.version_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def check_for_updates(self) -> tuple[bool, Dict]:
        """Проверка наличия обновлений на GitHub"""
        version_info = self.load_version_info()
        current_version = version_info['version']

        print(f"Текущая версия: {current_version}")

        try:
            response = requests.get(version_info['update_url'], timeout=10)
            response.raise_for_status()
            latest_release = response.json()

            latest_version = latest_release['tag_name'].lstrip('v')

            if self.compare_versions(latest_version, current_version) > 0:
                print(f"Доступна новая версия: {latest_version}")
                return True, latest_release
            else:
                print("У вас установлена последняя версия")
                return False, {}

        except Exception as e:
            print(f"Ошибка при проверке обновлений: {e}")
            return False, {}

    def compare_versions(self, version1: str, version2: str) -> int:
        """Сравнение версий (1 > 0 = новее, 0 = равны, -1 = старее)"""
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]

        for i in range(max(len(v1_parts), len(v2_parts))):
            v1 = v1_parts[i] if i < len(v1_parts) else 0
            v2 = v2_parts[i] if i < len(v2_parts) else 0

            if v1 > v2:
                return 1
            elif v1 < v2:
                return -1
        return 0

    def backup_critical_files(self) -> bool:
        """Резервное копирование важных файлов"""
        print("[3/4] Создание резервной копии...")

        version_info = self.load_version_info()
        critical_files = version_info.get('critical_files', [])

        if self.backup_dir.exists():
            shutil.rmtree(self.backup_dir)
        self.backup_dir.mkdir(exist_ok=True)

        try:
            for file_path in critical_files:
                source = self.project_root / file_path
                if source.exists():
                    dest = self.backup_dir / file_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, dest)
                    print(f"  ✓ Сохранён: {file_path}")
            return True
        except Exception as e:
            print(f"Ошибка при создании резервной копии: {e}")
            return False

    def download_update(self, release_info: Dict) -> Path:
        """Скачивание обновления"""
        print("[3/4] Загрузка обновления...")

        # Получаем ссылку на zip архив
        download_url = release_info['zipball_url']

        # Скачиваем во временную папку
        self.update_dir.mkdir(exist_ok=True)
        zip_path = self.update_dir / "update.zip"

        response = requests.get(download_url, stream=True)
        total_size = int(response.headers.get('content-length', 0))

        with open(zip_path, 'wb') as f:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    progress = (downloaded / total_size) * 100
                    print(f"\r  Загружено: {progress:.1f}%", end='')

        print("\n  ✓ Загрузка завершена")
        return zip_path

    def apply_update(self, zip_path: Path) -> bool:
        """Применение обновления"""
        print("[4/4] Установка обновления...")

        try:
            # Извлекаем архив
            extract_dir = self.update_dir / "extracted"
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            # GitHub создаёт папку с именем репозитория
            # Находим эту папку
            subdirs = [d for d in extract_dir.iterdir() if d.is_dir()]
            if not subdirs:
                raise Exception("Не найдена папка с обновлением")

            source_dir = subdirs[0]

            # Получаем список критических файлов
            version_info = self.load_version_info()
            critical_files = set(version_info.get('critical_files', []))

            # Копируем файлы, кроме критических
            for item in source_dir.rglob('*'):
                if item.is_file():
                    relative_path = item.relative_to(source_dir)

                    # Пропускаем критические файлы
                    if str(relative_path) in critical_files:
                        continue

                    # Пропускаем служебные папки
                    if any(part.startswith('.') for part in relative_path.parts):
                        continue

                    dest = self.project_root / relative_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest)

            print("  ✓ Файлы обновлены")

            # Восстанавливаем критические файлы из резервной копии
            self.restore_critical_files()

            # Очистка
            shutil.rmtree(self.update_dir)

            return True

        except Exception as e:
            print(f"Ошибка при применении обновления: {e}")
            print("Восстановление из резервной копии...")
            self.restore_from_backup()
            return False

    def restore_critical_files(self):
        """Восстановление критических файлов"""
        if not self.backup_dir.exists():
            return

        for item in self.backup_dir.rglob('*'):
            if item.is_file():
                relative_path = item.relative_to(self.backup_dir)
                dest = self.project_root / relative_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest)

    def restore_from_backup(self):
        """Полное восстановление из резервной копии"""
        if self.backup_dir.exists():
            self.restore_critical_files()
            print("Восстановление завершено")

    def run(self):
        """Основной процесс обновления"""
        print("Запуск процесса обновления...\n")

        # Проверка обновлений
        has_update, release_info = self.check_for_updates()

        if not has_update:
            return 0

        # Запрос подтверждения
        response = input("\nУстановить обновление? (y/n): ").lower()
        if response != 'y':
            print("Обновление отменено")
            return 0

        # Резервное копирование
        if not self.backup_critical_files():
            return 1

        # Загрузка обновления
        try:
            zip_path = self.download_update(release_info)
        except Exception as e:
            print(f"Ошибка при загрузке: {e}")
            return 1

        # Применение обновления
        if self.apply_update(zip_path):
            print("\n✓ Обновление успешно установлено!")

            # Удаление резервной копии
            if self.backup_dir.exists():
                shutil.rmtree(self.backup_dir)

            return 0
        else:
            return 1


if __name__ == "__main__":
    updater = ProjectUpdater()
    exit(updater.run())