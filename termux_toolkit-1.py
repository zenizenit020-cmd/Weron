#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Termux Toolkit — установка Python, полезных модулей и системных утилит.
Запуск:  python termux_toolkit.py
"""

import os
import subprocess
import sys
import base64
import secrets
import string
import hashlib
import zlib
import random

# ---------- Цвета (ANSI, без зависимостей) ----------
class C:
    R = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"


def title(t):
    print(f"\n{C.CYAN}{C.BOLD}{'═' * 50}{C.R}")
    print(f"{C.CYAN}{C.BOLD}  {t}{C.R}")
    print(f"{C.CYAN}{C.BOLD}{'═' * 50}{C.R}\n")


def ok(msg):
    print(f"{C.GREEN}[+]{C.R} {msg}")


def warn(msg):
    print(f"{C.YELLOW}[!]{C.R} {msg}")


def err(msg):
    print(f"{C.RED}[-]{C.R} {msg}")


def info(msg):
    print(f"{C.BLUE}[i]{C.R} {msg}")


def run(cmd, check=False):
    """Выполнить shell-команду с выводом в реальном времени."""
    info(f"Выполняю: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if check and result.returncode != 0:
        err(f"Команда завершилась с ошибкой (код {result.returncode})")
    return result.returncode == 0


def pause():
    input(f"\n{C.MAGENTA}Нажмите Enter, чтобы продолжить...{C.R}")


def is_termux():
    return "com.termux" in os.environ.get("PREFIX", "")


def has_termux_api():
    return run("command -v termux-battery-status > /dev/null 2>&1")


# ---------- Зависимости самого тулкита ----------
import importlib.util

# Строго обязательных внешних пакетов у тулкита нет — он специально написан
# на чистой стандартной библиотеке, чтобы стартовать сразу после установки Python.
# REQUIRED_DEPS оставлен на случай, если в будущем появится жёсткая зависимость:
# тогда main() откажется запускаться, пока пакет не установлен.
REQUIRED_DEPS = {
    # "имя_пакета": "почему без него софт не запустится",
}

# Необязательные пакеты — без них всё работает, но с ними отдельные функции
# становятся лучше/точнее/красивее. Если пакета нет, тулкит сам подставляет
# обычный shell-фолбэк, ничего не ломается.
RECOMMENDED_DEPS = {
    "qrcode": "Генерация QR-кодов в пункте меню (без него — предложит установить на месте)",
    "psutil": "Более точная и подробная информация о системе/батарее/процессах",
    "colorama": "Стабильный цветной вывод в терминалах, где сырые ANSI-коды глючат",
    "rich": "Красивые таблицы в списке модулей/зависимостей вместо обычного print()",
    "tqdm": "Прогресс-бар при хэшировании больших файлов и при установке пакетов",
    "requests": "Проверка интернет-соединения и своего публичного IP (self-check)",
    "pyperclip": "Буфер обмена вне Termux (Linux/Mac/Windows), когда нет Termux:API",
    "cryptography": "Настоящее AES-шифрование файла паролем (а не просто обфускация)",
    "pyfiglet": "Свои текстовые ASCII-баннеры разными шрифтами (не только логотип WERON)",
    "pillow": "Изменение размера/конвертация изображений в пункте утилит",
    "pyzbar": "Чтение QR-кодов из файла изображения (в паре с pillow)",
    "speedtest-cli": "Тест скорости интернета (пинг/скачивание/отдача)",
}


# Имя pip-пакета не всегда совпадает с именем модуля для import —
# здесь исключения, чтобы проверка не врала.
_IMPORT_NAME_OVERRIDES = {
    "pillow": "PIL",
    "speedtest-cli": "speedtest",
}


def _is_installed(pkg):
    import_name = _IMPORT_NAME_OVERRIDES.get(pkg, pkg)
    return importlib.util.find_spec(import_name) is not None


def check_dependencies():
    """Возвращает (missing_required, missing_recommended) — списки имён пакетов."""
    missing_required = [p for p in REQUIRED_DEPS if not _is_installed(p)]
    missing_recommended = [p for p in RECOMMENDED_DEPS if not _is_installed(p)]
    return missing_required, missing_recommended


# В Termux некоторые пакеты требуют компиляции нативного кода (C/Rust), что на
# Android через голый pip не соберётся — зато в Termux есть готовые бинарные
# сборки через pkg. Здесь — какие ставить через pkg вместо pip, и какие
# нативные библиотеки нужно поставить перед pip-установкой чистого враппера.
TERMUX_PKG_OVERRIDES = {
    "psutil": "python-psutil",
    "pillow": "python-pillow",
    "cryptography": "python-cryptography",
}
TERMUX_NATIVE_PREREQS = {
    "pyzbar": ["libzbar"],
}


def install_packages(packages):
    if not packages:
        return

    termux = is_termux()

    # В Termux пакет pip управляется через pkg, самообновление через
    # "pip install --upgrade pip" там запрещено и всегда падает с ошибкой —
    # апгрейдим pip только вне Termux.
    if termux:
        run("pkg install -y python-pip")
    else:
        run("pip install --upgrade pip")

    pip_packages = []
    for pkg in packages:
        if termux and pkg in TERMUX_PKG_OVERRIDES:
            run(f"pkg install -y {TERMUX_PKG_OVERRIDES[pkg]}")
        else:
            if termux and pkg in TERMUX_NATIVE_PREREQS:
                for native in TERMUX_NATIVE_PREREQS[pkg]:
                    run(f"pkg install -y {native}")
            pip_packages.append(pkg)

    if not pip_packages:
        ok("Готово.")
        return

    if _is_installed("tqdm") and len(pip_packages) > 1:
        from tqdm import tqdm
        failed = []
        for pkg in tqdm(pip_packages, desc="Установка пакетов", unit="пакет"):
            if not run(f"pip install {pkg}"):
                failed.append(pkg)
        if failed:
            err(f"Не получилось установить: {', '.join(failed)}")
        else:
            ok(f"Установлено: {', '.join(pip_packages)}")
    else:
        pkgs = " ".join(pip_packages)
        ok_flag = run(f"pip install {pkgs}")
        if ok_flag:
            ok(f"Установлено: {pkgs}")
        else:
            err(f"Не получилось установить: {pkgs}")


def ensure_required_dependencies():
    """Вызывается при старте. Если появится жёсткая зависимость в REQUIRED_DEPS —
    без неё тулкит откажется работать, пока пакет не будет установлен."""
    missing, _ = check_dependencies()
    if not missing:
        return True
    title("НУЖНЫ ОБЯЗАТЕЛЬНЫЕ МОДУЛИ")
    for pkg in missing:
        err(f"{pkg} — {REQUIRED_DEPS[pkg]}")
    choice = input(
        f"\n{C.CYAN}Без этих модулей софт не запустится. Установить сейчас? [Y/n]: {C.R}"
    ).strip().lower()
    if choice in ("", "y", "yes", "д", "да"):
        install_packages(missing)
        still_missing, _ = check_dependencies()
        if still_missing:
            err("Не все обязательные модули установлены. Софт не может продолжить.")
            sys.exit(1)
        return True
    err("Без обязательных модулей продолжить нельзя.")
    sys.exit(1)


def menu_dependencies():
    while True:
        title("МОДУЛИ, КОТОРЫЕ ИСПОЛЬЗУЕТ ТУЛКИТ")
        missing_req, missing_rec = check_dependencies()

        if REQUIRED_DEPS:
            print(f"  {C.BOLD}Обязательные (без них софт не работает):{C.R}")
            for pkg, why in REQUIRED_DEPS.items():
                status = f"{C.RED}не установлен{C.R}" if pkg in missing_req else f"{C.GREEN}установлен{C.R}"
                print(f"    {pkg:<10} [{status}] — {why}")
        else:
            info("Обязательных внешних модулей нет — тулкит работает на чистом stdlib.")

        print(f"\n  {C.BOLD}Рекомендуемые (помогают софту работать лучше):{C.R}")
        for pkg, why in RECOMMENDED_DEPS.items():
            status = f"{C.YELLOW}не установлен{C.R}" if pkg in missing_rec else f"{C.GREEN}установлен{C.R}"
            print(f"    {pkg:<10} [{status}] — {why}")

        print(f"\n  {C.YELLOW}A{C.R}. Установить все недостающие")
        print(f"  {C.YELLOW}R{C.R}. Установить недостающие обязательные")
        print(f"  {C.YELLOW}0{C.R}. Назад")

        choice = input(f"\n{C.CYAN}Выбор: {C.R}").strip().lower()
        if choice == "0":
            return
        elif choice == "a":
            install_packages(missing_req + missing_rec)
            pause()
        elif choice == "r":
            install_packages(missing_req)
            pause()
        else:
            err("Неверный выбор.")
            pause()


# ---------- 1. Установка версии Python ----------
PYTHON_VERSIONS = {
    "1": ("python", "Последняя версия (главный пакет Termux)"),
    "2": ("python3.13", "Python 3.13 (tur-packages)"),
    "3": ("python3.12", "Python 3.12"),
    "4": ("python3.11", "Python 3.11 (tur-packages)"),
    "5": ("python3.10", "Python 3.10 (tur-packages)"),
    "6": ("python3.9", "Python 3.9 (tur-packages)"),
}


def menu_install_python():
    title("УСТАНОВКА ВЕРСИИ PYTHON")
    for key, (pkg, desc) in PYTHON_VERSIONS.items():
        print(f"  {C.YELLOW}{key}{C.R}. {pkg:<12} — {desc}")
    print(f"  {C.YELLOW}0{C.R}. Назад")

    choice = input(f"\n{C.CYAN}Выберите версию: {C.R}").strip()
    if choice == "0":
        return
    if choice not in PYTHON_VERSIONS:
        err("Неверный выбор.")
        pause()
        return

    pkg, desc = PYTHON_VERSIONS[choice]
    run("pkg update -y")
    run(f"pkg install -y {pkg}")

    if pkg != "python":
        ver = pkg.replace("python", "")
        make_default = input(
            f"\n{C.CYAN}Сделать {pkg} версией по умолчанию (команда python)? [y/N]: {C.R}"
        ).strip().lower()
        if make_default == "y":
            run("pkg uninstall -y python 2>/dev/null")
            run(f"pkg install -y python-is-python{ver}")
            run("pkg install -y python-pip")

    ok("Готово.")
    run("python --version 2>/dev/null || echo 'Проверьте: python3.X --version'")
    pause()


# ---------- 2. Полезные модули ----------
USEFUL_MODULES = [
    ("requests", "HTTP-запросы"),
    ("rich", "Красивый вывод в консоль (таблицы, прогресс-бары)"),
    ("colorama", "Цветной текст в терминале"),
    ("beautifulsoup4", "Парсинг HTML/веб-скрапинг"),
    ("lxml", "Быстрый XML/HTML парсер"),
    ("pandas", "Работа с таблицами и данными"),
    ("pillow", "Обработка изображений"),
    ("fake_useragent", "Генерация случайных User-Agent"),
    ("pyfiglet", "ASCII-арт заголовки"),
    ("termcolor", "Цветной текст (альтернатива colorama)"),
    ("tqdm", "Прогресс-бары"),
    ("python-dotenv", "Работа с .env файлами (переменные окружения)"),
    ("qrcode", "Генерация QR-кодов"),
    ("psutil", "Информация о системе и процессах"),
    ("pyzbar", "Чтение QR-кодов из изображений"),
    ("cryptography", "Настоящее шифрование файлов"),
    ("speedtest-cli", "Тест скорости интернета"),
]


def menu_install_modules():
    title("ПОЛЕЗНЫЕ МОДУЛИ PYTHON")
    for i, (mod, desc) in enumerate(USEFUL_MODULES, 1):
        print(f"  {C.YELLOW}{i}{C.R}. {mod:<16} — {desc}")
    print(f"\n  {C.YELLOW}A{C.R}. Установить всё")
    print(f"  {C.YELLOW}0{C.R}. Назад")

    choice = input(
        f"\n{C.CYAN}Введите номера через запятую (напр. 1,3,5) или A: {C.R}"
    ).strip()

    if choice == "0":
        return

    if choice.lower() == "a":
        selected = [m for m, _ in USEFUL_MODULES]
    else:
        selected = []
        for part in choice.split(","):
            part = part.strip()
            if part.isdigit() and 1 <= int(part) <= len(USEFUL_MODULES):
                selected.append(USEFUL_MODULES[int(part) - 1][0])

    if not selected:
        warn("Ничего не выбрано.")
        pause()
        return

    install_packages(selected)
    pause()


# ---------- 3. Системные утилиты ----------
def util_update_pip():
    title("ОБНОВЛЕНИЕ PIP И PKG")
    run("pkg update -y && pkg upgrade -y")
    if is_termux():
        # В Termux pip обновляется через pkg, а не через себя же —
        # "pip install --upgrade pip" там запрещён и всегда падает.
        run("pkg install -y python-pip")
    else:
        run("pip install --upgrade pip")
    ok("Обновлено.")
    pause()


def util_backup_packages():
    title("БЭКАП СПИСКА ПАКЕТОВ")
    path = os.path.expanduser("~/termux_backup.txt")
    with open(path, "w") as f:
        f.write("# pkg packages\n")
    run(f"pkg list-installed >> {path}")
    with open(path, "a") as f:
        f.write("\n# pip packages\n")
    run(f"pip freeze >> {path}")
    ok(f"Бэкап сохранён: {path}")
    pause()


def util_storage_permission():
    title("ДОСТУП К ПАМЯТИ ТЕЛЕФОНА")
    run("termux-setup-storage")
    pause()


def util_clean_cache():
    title("ОЧИСТКА КЭША И ВРЕМЕННЫХ ФАЙЛОВ")
    run("pip cache purge")
    run("pkg clean")
    run("rm -rf ~/.cache/pip/* 2>/dev/null")
    ok("Кэш очищен.")
    pause()


def util_dev_essentials():
    title("УСТАНОВКА БАЗОВЫХ DEV-ИНСТРУМЕНТОВ")
    print(f"  {C.YELLOW}1{C.R}. git")
    print(f"  {C.YELLOW}2{C.R}. nano / vim")
    print(f"  {C.YELLOW}3{C.R}. openssh (ssh-клиент/сервер)")
    print(f"  {C.YELLOW}4{C.R}. nodejs")
    print(f"  {C.YELLOW}5{C.R}. zip / unzip")
    print(f"  {C.YELLOW}A{C.R}. Установить всё")
    print(f"  {C.YELLOW}0{C.R}. Назад")

    choice = input(f"\n{C.CYAN}Выбор: {C.R}").strip().lower()
    mapping = {
        "1": "git",
        "2": "nano vim",
        "3": "openssh",
        "4": "nodejs",
        "5": "zip unzip",
    }
    if choice == "0":
        return
    if choice == "a":
        run("pkg install -y git nano vim openssh nodejs zip unzip")
    elif choice in mapping:
        run(f"pkg install -y {mapping[choice]}")
    else:
        err("Неверный выбор.")
    ok("Готово.")
    pause()


def util_ssh_server():
    title("ЗАПУСК SSH-СЕРВЕРА В TERMUX")
    if not run("command -v sshd > /dev/null 2>&1"):
        info("openssh не установлен, устанавливаю...")
        run("pkg install -y openssh")
    run("sshd")
    ok("SSH-сервер запущен (обычно порт 8022).")
    run("whoami")
    run("ifconfig 2>/dev/null | grep -A1 wlan0 || ip addr show 2>/dev/null")
    info("Подключение: ssh -p 8022 <пользователь>@<локальный_IP>")
    pause()


def util_git_setup():
    title("НАСТРОЙКА GIT")
    name = input(f"{C.CYAN}Имя пользователя для git: {C.R}").strip()
    email = input(f"{C.CYAN}Email для git: {C.R}").strip()
    if name:
        run(f'git config --global user.name "{name}"')
    if email:
        run(f'git config --global user.email "{email}"')
    run('git config --global init.defaultBranch main')
    ok("Настройки git сохранены.")
    pause()


def util_password_generator():
    title("ГЕНЕРАТОР ПАРОЛЕЙ")
    try:
        length = int(input(f"{C.CYAN}Длина пароля (по умолчанию 16): {C.R}").strip() or 16)
    except ValueError:
        length = 16
    count = input(f"{C.CYAN}Сколько паролей сгенерировать (по умолчанию 1): {C.R}").strip()
    count = int(count) if count.isdigit() else 1
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    for _ in range(count):
        pw = "".join(secrets.choice(alphabet) for _ in range(length))
        print(f"  {C.GREEN}{pw}{C.R}")
    pause()


def util_file_hash():
    title("ХЭШ ФАЙЛА (MD5 / SHA256)")
    path = input(f"{C.CYAN}Путь к файлу: {C.R}").strip()
    path = os.path.expanduser(path)
    if not os.path.isfile(path):
        err("Файл не найден.")
        pause()
        return
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()
    size = os.path.getsize(path)

    progress = None
    if _is_installed("tqdm") and size > 5 * 1024 * 1024:  # показываем бар только для файлов >5МБ
        from tqdm import tqdm
        progress = tqdm(total=size, unit="B", unit_scale=True, desc="Хэширую")

    with open(path, "rb") as f:
        while chunk := f.read(8192):
            md5.update(chunk)
            sha256.update(chunk)
            if progress:
                progress.update(len(chunk))
    if progress:
        progress.close()

    print(f"  MD5:    {C.GREEN}{md5.hexdigest()}{C.R}")
    print(f"  SHA256: {C.GREEN}{sha256.hexdigest()}{C.R}")
    pause()


def util_qr_generate():
    title("ГЕНЕРАЦИЯ QR-КОДА (в терминале)")
    try:
        import qrcode
    except ImportError:
        warn("Модуль qrcode не установлен. Устанавливаю...")
        run("pip install qrcode")
        try:
            import qrcode
        except ImportError:
            err("Не удалось установить qrcode.")
            pause()
            return
    text = input(f"{C.CYAN}Текст / ссылка для QR-кода: {C.R}").strip()
    if not text:
        pause()
        return
    qr = qrcode.QRCode(border=1)
    qr.add_data(text)
    qr.make()
    qr.print_ascii(invert=True)
    pause()


def util_termux_api_battery():
    title("СТАТУС БАТАРЕИ")
    if not has_termux_api():
        warn("Пакет termux-api не установлен или приложение Termux:API не установлено.")
        install = input(f"{C.CYAN}Установить пакет termux-api? [y/N]: {C.R}").strip().lower()
        if install == "y":
            run("pkg install -y termux-api")
        pause()
        return
    run("termux-battery-status")
    pause()


def util_termux_api_clipboard():
    title("БУФЕР ОБМЕНА")
    use_termux = has_termux_api()
    use_pyperclip = (not use_termux) and _is_installed("pyperclip")

    if not use_termux and not use_pyperclip:
        warn("Нет ни termux-api, ни модуля pyperclip — буфер обмена недоступен.")
        info("В Termux: pkg install termux-api. Вне Termux: pip install pyperclip.")
        pause()
        return

    print(f"  {C.YELLOW}1{C.R}. Показать содержимое буфера")
    print(f"  {C.YELLOW}2{C.R}. Записать текст в буфер")
    choice = input(f"\n{C.CYAN}Выбор: {C.R}").strip()

    if choice == "1":
        if use_termux:
            run("termux-clipboard-get")
        else:
            import pyperclip
            print(f"  {pyperclip.paste()}")
    elif choice == "2":
        text = input(f"{C.CYAN}Текст: {C.R}")
        if use_termux:
            subprocess.run(["termux-clipboard-set"], input=text.encode())
        else:
            import pyperclip
            pyperclip.copy(text)
        ok("Скопировано в буфер.")
    pause()


def util_termux_api_notify():
    title("ОТПРАВИТЬ УВЕДОМЛЕНИЕ")
    if not has_termux_api():
        warn("Пакет termux-api не установлен.")
        pause()
        return
    text = input(f"{C.CYAN}Текст уведомления: {C.R}").strip()
    if text:
        run(f'termux-notification --content "{text}"')
        ok("Уведомление отправлено.")
    pause()


def util_system_info():
    title("ИНФОРМАЦИЯ О СИСТЕМЕ")
    if _is_installed("psutil"):
        import psutil
        vm = psutil.virtual_memory()
        du = psutil.disk_usage(os.environ.get("PREFIX", "/"))
        print(f"  CPU:     {psutil.cpu_percent(interval=0.3)}% "
              f"({psutil.cpu_count()} ядер)")
        print(f"  RAM:     {vm.used // (1024**2)} / {vm.total // (1024**2)} МБ "
              f"({vm.percent}%)")
        print(f"  Диск:    {du.used // (1024**2)} / {du.total // (1024**2)} МБ "
              f"({du.percent}%)")
        battery = psutil.sensors_battery()
        if battery:
            print(f"  Батарея: {battery.percent}% "
                  f"({'заряжается' if battery.power_plugged else 'от батареи'})")
    else:
        info("Модуль psutil не установлен — показываю через shell-команды "
             "(поставь psutil в разделе «Модули софта» для более точных данных).")
        run("uname -a")
        run("df -h $PREFIX 2>/dev/null")
        run("free -h 2>/dev/null || cat /proc/meminfo | head -3")
    pause()


def util_network_check():
    """Проверка своего интернет-соединения и своего же публичного IP —
    self-диагностика устройства, а не поиск информации о других людях."""
    title("ПРОВЕРКА ИНТЕРНЕТ-СОЕДИНЕНИЯ")
    if not _is_installed("requests"):
        warn("Модуль requests не установлен — ставится в «6. Модули софта».")
        info("Пробую через curl...")
        run("curl -s -o /dev/null -w 'HTTP статус: %{http_code}\\n' https://api.ipify.org", check=True)
        run("curl -s https://api.ipify.org && echo")
        pause()
        return

    import requests
    try:
        r = requests.get("https://api.ipify.org?format=json", timeout=5)
        ok(f"Интернет работает. Мой публичный IP: {r.json().get('ip')}")
    except requests.RequestException as e:
        err(f"Нет соединения или сайт недоступен: {e}")
    pause()


def util_speed_test():
    title("ТЕСТ СКОРОСТИ ИНТЕРНЕТА")
    if not _is_installed("speedtest-cli"):
        warn("Модуль speedtest-cli не установлен — ставится в «6. Модули софта».")
        pause()
        return
    import speedtest
    info("Замеряю скорость, это займёт около 20-30 секунд...")
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        down = st.download() / 1_000_000
        up = st.upload() / 1_000_000
        ping = st.results.ping
        print(f"  Пинг:    {C.GREEN}{ping:.0f} мс{C.R}")
        print(f"  Скачивание: {C.GREEN}{down:.1f} Мбит/с{C.R}")
        print(f"  Отдача:  {C.GREEN}{up:.1f} Мбит/с{C.R}")
    except Exception as e:
        err(f"Не удалось пройти тест: {e}")
    pause()


def util_custom_banner():
    title("СВОЙ ASCII-БАННЕР (pyfiglet)")
    if not _is_installed("pyfiglet"):
        warn("Модуль pyfiglet не установлен — ставится в «6. Модули софта».")
        pause()
        return
    import pyfiglet
    text = input(f"{C.CYAN}Текст для баннера: {C.R}").strip()
    if not text:
        pause()
        return
    fonts = ["standard", "big", "block", "banner3-D", "doom", "slant"]
    print(f"\n{C.CYAN}Доступные шрифты: {', '.join(fonts)}{C.R}")
    font = input(f"{C.CYAN}Шрифт (Enter — standard): {C.R}").strip() or "standard"
    try:
        print(f"\n{C.BLUE}{pyfiglet.figlet_format(text, font=font)}{C.R}")
    except pyfiglet.FontNotFound:
        err(f"Шрифт «{font}» не найден, использую standard.")
        print(f"\n{C.BLUE}{pyfiglet.figlet_format(text)}{C.R}")
    pause()


def util_image_resize():
    title("ИЗМЕНЕНИЕ РАЗМЕРА / КОНВЕРТАЦИЯ ИЗОБРАЖЕНИЯ")
    if not _is_installed("pillow"):
        warn("Модуль pillow не установлен — ставится в «6. Модули софта».")
        pause()
        return
    from PIL import Image
    path = os.path.expanduser(input(f"{C.CYAN}Путь к изображению: {C.R}").strip())
    if not os.path.isfile(path):
        err("Файл не найден.")
        pause()
        return
    try:
        img = Image.open(path)
    except Exception as e:
        err(f"Не удалось открыть изображение: {e}")
        pause()
        return

    info(f"Текущий размер: {img.width}x{img.height}, формат: {img.format}")
    width_in = input(f"{C.CYAN}Новая ширина в пикселях (Enter — не менять): {C.R}").strip()
    out_format = input(f"{C.CYAN}Формат вывода (png/jpg, Enter — как есть): {C.R}").strip().lower()

    if width_in.isdigit():
        w = int(width_in)
        h = int(img.height * (w / img.width))
        img = img.resize((w, h))

    base, ext = os.path.splitext(path)
    if out_format in ("png", "jpg", "jpeg"):
        ext = "." + ("jpg" if out_format == "jpeg" else out_format)
        if ext == ".jpg" and img.mode == "RGBA":
            img = img.convert("RGB")
    out_path = base + "_edited" + ext
    img.save(out_path)
    ok(f"Сохранено: {out_path}")
    pause()


def util_qr_decode():
    title("ЧТЕНИЕ QR-КОДА ИЗ ИЗОБРАЖЕНИЯ")
    if not _is_installed("pillow") or not _is_installed("pyzbar"):
        warn("Нужны модули pillow и pyzbar — ставятся в «6. Модули софта».")
        pause()
        return
    from PIL import Image
    from pyzbar.pyzbar import decode
    path = os.path.expanduser(input(f"{C.CYAN}Путь к изображению с QR-кодом: {C.R}").strip())
    if not os.path.isfile(path):
        err("Файл не найден.")
        pause()
        return
    results = decode(Image.open(path))
    if not results:
        warn("QR-код не найден на изображении.")
    for r in results:
        ok(r.data.decode(errors="replace"))
    pause()


def menu_utils():
    while True:
        title("ПОЛЕЗНЫЕ ФИШКИ")
        print(f"  {C.YELLOW}1{C.R}.  Обновить pkg и pip")
        print(f"  {C.YELLOW}2{C.R}.  Сделать бэкап списка пакетов")
        print(f"  {C.YELLOW}3{C.R}.  Выдать Termux доступ к памяти телефона")
        print(f"  {C.YELLOW}4{C.R}.  Очистить кэш pip/pkg")
        print(f"  {C.YELLOW}5{C.R}.  Установить базовые dev-инструменты (git, nano, ssh...)")
        print(f"  {C.YELLOW}6{C.R}.  Запустить SSH-сервер")
        print(f"  {C.YELLOW}7{C.R}.  Настроить git (имя/email)")
        print(f"  {C.YELLOW}8{C.R}.  Генератор паролей")
        print(f"  {C.YELLOW}9{C.R}.  Хэш файла (MD5/SHA256)")
        print(f"  {C.YELLOW}10{C.R}. Сгенерировать QR-код")
        print(f"  {C.YELLOW}11{C.R}. Статус батареи (Termux:API)")
        print(f"  {C.YELLOW}12{C.R}. Буфер обмена (Termux:API)")
        print(f"  {C.YELLOW}13{C.R}. Отправить уведомление (Termux:API)")
        print(f"  {C.YELLOW}14{C.R}. Информация о системе")
        print(f"  {C.YELLOW}15{C.R}. Проверка интернета и своего IP")
        print(f"  {C.YELLOW}16{C.R}. Тест скорости интернета")
        print(f"  {C.YELLOW}17{C.R}. Свой ASCII-баннер (pyfiglet)")
        print(f"  {C.YELLOW}18{C.R}. Изменить размер/конвертировать изображение")
        print(f"  {C.YELLOW}19{C.R}. Прочитать QR-код из файла")
        print(f"  {C.YELLOW}0{C.R}.  Назад")

        choice = input(f"\n{C.CYAN}Выбор: {C.R}").strip()
        actions = {
            "1": util_update_pip,
            "2": util_backup_packages,
            "3": util_storage_permission,
            "4": util_clean_cache,
            "5": util_dev_essentials,
            "6": util_ssh_server,
            "7": util_git_setup,
            "8": util_password_generator,
            "9": util_file_hash,
            "10": util_qr_generate,
            "11": util_termux_api_battery,
            "12": util_termux_api_clipboard,
            "13": util_termux_api_notify,
            "14": util_system_info,
            "15": util_network_check,
            "16": util_speed_test,
            "17": util_custom_banner,
            "18": util_image_resize,
            "19": util_qr_decode,
        }
        if choice == "0":
            return
        elif choice in actions:
            actions[choice]()
        else:
            err("Неверный выбор.")
            pause()


# ---------- 4. Обфускация скрипта ----------
def menu_obfuscate():
    """
    Простое сокрытие исходного кода (base64 + zlib), НЕ настоящее шифрование.
    Обфусцированный файл при запуске распаковывает и выполняет исходный код.
    Любой человек с доступом к файлу и Python может декодировать base64 обратно —
    это защищает только от беглого просмотра "что тут написано", а не от анализа.
    Для реальной защиты интеллектуальной собственности нужны другие инструменты
    (например, компиляция в бинарь), но и они не дают стопроцентной гарантии.
    """
    title("ОБФУСКАЦИЯ PYTHON-СКРИПТА")
    info("Это скрытие кода (base64+zlib), а не настоящее шифрование.")
    info("Обфусцированный файл по-прежнему исполняет тот же код.")
    src_path = input(f"{C.CYAN}Путь к .py файлу для обфускации: {C.R}").strip()
    src_path = os.path.expanduser(src_path)
    if not os.path.isfile(src_path):
        err("Файл не найден.")
        pause()
        return

    with open(src_path, "rb") as f:
        source = f.read()

    compressed = zlib.compress(source, level=9)
    encoded = base64.b85encode(compressed).decode()

    out_path = os.path.splitext(src_path)[0] + "_obf.py"
    wrapper = (
        "#!/usr/bin/env python3\n"
        "# Обфусцировано Termux Toolkit — исходный код скрыт, не зашифрован.\n"
        "import base64, zlib\n"
        f"_payload = {encoded!r}\n"
        "exec(zlib.decompress(base64.b85decode(_payload)))\n"
    )

    with open(out_path, "w") as f:
        f.write(wrapper)

    ok(f"Обфусцированный файл сохранён: {out_path}")
    warn("Помните: это не защита от серьёзного анализа, только от чтения глазами.")
    pause()


def util_encrypt_file_real():
    """Настоящее AES-шифрование файла паролем через cryptography.Fernet.
    В отличие от обфускации выше, зашифрованный файл нельзя прочитать или
    выполнить без пароля — ключ получается через PBKDF2 из пароля и соли."""
    title("НАСТОЯЩЕЕ ШИФРОВАНИЕ ФАЙЛА ПАРОЛЕМ (AES, cryptography)")
    if not _is_installed("cryptography"):
        warn("Модуль cryptography не установлен — ставится в «6. Модули софта».")
        pause()
        return

    import getpass
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    print(f"  {C.YELLOW}1{C.R}. Зашифровать файл")
    print(f"  {C.YELLOW}2{C.R}. Расшифровать файл")
    action = input(f"\n{C.CYAN}Выбор: {C.R}").strip()
    if action not in ("1", "2"):
        err("Неверный выбор.")
        pause()
        return

    path = os.path.expanduser(input(f"{C.CYAN}Путь к файлу: {C.R}").strip())
    if not os.path.isfile(path):
        err("Файл не найден.")
        pause()
        return

    password = getpass.getpass(f"{C.CYAN}Пароль: {C.R}").encode()

    if action == "1":
        salt = secrets.token_bytes(16)
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=390000)
        key = base64.urlsafe_b64encode(kdf.derive(password))
        with open(path, "rb") as f:
            data = f.read()
        token = Fernet(key).encrypt(data)
        out_path = path + ".enc"
        with open(out_path, "wb") as f:
            f.write(salt + token)  # соль (16 байт) + зашифрованные данные
        ok(f"Зашифровано: {out_path}")
        warn("Пароль нигде не сохраняется — если забудешь, файл не восстановить.")
    else:
        with open(path, "rb") as f:
            raw = f.read()
        salt, token = raw[:16], raw[16:]
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=390000)
        key = base64.urlsafe_b64encode(kdf.derive(password))
        try:
            data = Fernet(key).decrypt(token)
        except Exception:
            err("Неверный пароль или повреждённый файл.")
            pause()
            return
        out_path = path[:-4] if path.endswith(".enc") else path + ".dec"
        with open(out_path, "wb") as f:
            f.write(data)
        ok(f"Расшифровано: {out_path}")
    pause()


# ---------- Главное меню ----------

# Простой блочный 5x7 пиксельный шрифт для ASCII-логотипа (без внешних зависимостей)
_FONT_5x7 = {
    "W": ["10001", "10001", "10001", "10101", "10101", "11011", "10001"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "N": ["10001", "11001", "10101", "10101", "10011", "10001", "10001"],
}
_LOGO_SHADES = ["\033[38;5;27m", "\033[38;5;33m", "\033[38;5;39m",
                "\033[38;5;45m", "\033[38;5;51m"]
_LOGO_DRIP = "\033[38;5;24m"


_LOGO_TRUECOLOR_STOPS = [(20, 40, 130), (30, 80, 200), (40, 120, 230),
                         (60, 160, 245), (90, 200, 255)]
_LOGO_DRIP_RGB = (25, 55, 150)


def _supports_truecolor():
    return os.environ.get("COLORTERM", "") in ("truecolor", "24bit")


def _rgb(r, g, b):
    return f"\033[38;2;{r};{g};{b}m"


def _lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _gradient_color(row_index, total_rows):
    stops = _LOGO_TRUECOLOR_STOPS
    t = row_index / max(total_rows - 1, 1)
    seg = t * (len(stops) - 1)
    i = min(int(seg), len(stops) - 2)
    local_t = seg - i
    return _lerp_color(stops[i], stops[i + 1], local_t)


def render_logo(text, pad=2, drip_rows=2, seed=7):
    """Рендерит текст крупным блочным ASCII-логотипом с синим градиентом и
    эффектом «капель» снизу. Использует truecolor (24-бит), если терминал
    его поддерживает (COLORTERM=truecolor/24bit), иначе — 256-цветный фолбэк."""
    truecolor = _supports_truecolor()
    rows = ["" for _ in range(7)]
    for ch in text:
        glyph = _FONT_5x7.get(ch.upper())
        if not glyph:
            continue
        for r in range(7):
            block = "".join("██" if b == "1" else "  " for b in glyph[r])
            rows[r] += block + " " * pad

    lines = []
    for i, row in enumerate(rows):
        if truecolor:
            r, g, b = _gradient_color(i, len(rows))
            color = _rgb(r, g, b)
        else:
            color = _LOGO_SHADES[min(i, len(_LOGO_SHADES) - 1)]
        lines.append(color + row + C.R)

    rng = random.Random(seed)
    drip_chars = "▓▒░"
    drip_color = _rgb(*_LOGO_DRIP_RGB) if truecolor else _LOGO_DRIP
    for r in range(drip_rows):
        line = ""
        for ch in text:
            glyph = _FONT_5x7.get(ch.upper())
            if not glyph:
                continue
            width = len(glyph[0]) * 2
            threshold = 0.5 - r * 0.15
            for _ in range(width):
                line += rng.choice(drip_chars) if rng.random() < threshold else " "
            line += " " * pad
        lines.append(drip_color + line + C.R)

    return "\n".join(lines)


def print_banner():
    print(render_logo("WERON"))
    print(
        f"\n  {C.CYAN}dev> {C.R}your_handle    "
        f"{C.CYAN}version{C.R} 1.0    "
        f"{C.CYAN}Python · Модули · Утилиты · Обфускация{C.R}\n"
    )


def main():
    if not is_termux():
        warn("Похоже, скрипт запущен не в Termux. Некоторые команды (pkg) могут не сработать.")

    # colorama стабилизирует ANSI-цвета там, где они по умолчанию не работают
    # (в Termux почти всегда не нужен, но не мешает и подстраховывает).
    if _is_installed("colorama"):
        import colorama
        colorama.init(autoreset=False)

    # Обязательные зависимости (если появятся) — без них не идём дальше.
    ensure_required_dependencies()

    # Рекомендованные зависимости — не блокируют запуск, просто одно ненавязчивое
    # напоминание в начале сессии.
    _, missing_rec = check_dependencies()
    if missing_rec:
        warn(
            "Не хватает необязательных модулей ("
            + ", ".join(missing_rec)
            + ") — софт работает и без них, но с ними лучше. "
              "Пункт «6. Модули софта» в главном меню."
        )
        pause()

    while True:
        os.system("clear" if os.name != "nt" else "cls")
        print_banner()
        print(f"  {C.YELLOW}1{C.R}. Установить версию Python")
        print(f"  {C.YELLOW}2{C.R}. Установить полезные модули")
        print(f"  {C.YELLOW}3{C.R}. Полезные утилиты")
        print(f"  {C.YELLOW}4{C.R}. Обфусцировать .py скрипт (скрыть, не зашифровать)")
        print(f"  {C.YELLOW}5{C.R}. Настоящее AES-шифрование файла паролем")
        print(f"  {C.YELLOW}6{C.R}. Модули софта (обязательные/рекомендуемые)")
        print(f"  {C.YELLOW}0{C.R}. Выход")

        choice = input(f"\n{C.CYAN}Выбор: {C.R}").strip()

        if choice == "1":
            menu_install_python()
        elif choice == "2":
            menu_install_modules()
        elif choice == "3":
            menu_utils()
        elif choice == "4":
            menu_obfuscate()
        elif choice == "5":
            util_encrypt_file_real()
        elif choice == "6":
            menu_dependencies()
        elif choice == "0":
            print(f"\n{C.GREEN}Пока!{C.R}\n")
            sys.exit(0)
        else:
            err("Неверный выбор.")
            pause()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{C.YELLOW}Прервано пользователем.{C.R}")
        sys.exit(0)
