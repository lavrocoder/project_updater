import json

import requests


def check_updates_on_startup():
    """Проверка обновлений при запуске (без установки)"""
    try:
        with open('version.json', 'r') as f:
            version_info = json.load(f)

        response = requests.get(version_info['update_url'], timeout=5)
        latest = response.json()['tag_name'].lstrip('v')
        current = version_info['version']

        if latest != current:
            print(f"⚠ Доступно обновление {latest}. Запустите update.bat")
    except:
        pass  # Тихо игнорируем ошибки проверки


if __name__ == "__main__":
    check_updates_on_startup()