import os
import logging
import time
import sys
from datetime import datetime

import getpass
from rich.console import Console
from colorama import Fore, Style as ColoramaStyle
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit import HTML
from prompt_toolkit import print_formatted_text
from prompt_toolkit.styles import Style
from prompt_toolkit.application import get_app

from crypto_layer import CryptoLayer
from UIProvider import UIProvider

import module_manager
from base_module import BaseModule

import modules.hidden_imports


pt_session = PromptSession()
console = Console()
console_status = console.status("...")

LOGGER = None
LOGS_TO_FILE = True
PRINT_LOGS = False

CURRENT_DIR = os.getcwd()
DATA_DIR = os.path.join(CURRENT_DIR, 'data')
LOGS_FILE_PATH = os.path.join(CURRENT_DIR, 'crypto_layer.log')

ON_READY = False

MODULE_CLASS = None

clayer = None


class TerminalUI(UIProvider):

    # Запрос чего-либо. Возвращаемые данные должны соответствовать data_type
    def request_data(self, prompt: str, data_type: type):
        console_status.stop()
        while True:
            try:
                user_input = input(f"{prompt}: {Fore.GREEN}").strip()
                print(ColoramaStyle.RESET_ALL, end="")

                if data_type is bool:
                    normalized = user_input.strip().lower()
                    if normalized in ('true', '1', 'yes', 'y'):
                        console_status.start()
                        return True
                    if normalized in ('false', '0', 'no', 'n', ''):
                        console_status.start()
                        return False
                    error("Could not parse boolean value (True/False)")
                    continue

                converted_data = data_type(user_input)
                console_status.start()
                return converted_data

            except (ValueError, TypeError) as e:
                error(f"The entered data does not match the required type {data_type.__name__}!")

    # Передать в UI текст состояния
    def update_status(self, stage: str, message: str, status_type: str = "in_progress"):
        if status_type == "in_progress":
            console_status.start()
            console_status.update(f"[*] {stage}: [yellow]{message}[/yellow]")
        elif status_type == "error":
            console_status.start()
            console_status.update(f"[x] {stage}: [red]{message}[/red]")
        elif status_type == "success":
            console_status.stop()
            console.print(f"[+] {stage}: [green]{message}[/green]")


    # Новое сообщение. Передаем его в UI
    def on_text_received(self, timestamp: int, text: str):
        time_string = datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')
        with patch_stdout():
            print_formatted_text(HTML(f'<ansiblue>peer [{time_string}]:</ansiblue> {text}'))

    # Проверка подписей на правильность
    # Возвращает True ДА или False НЕТ
    def check_signatures(self, my_sign: str, companion_sign: str) -> bool:
        console_status.stop()
        print_formatted_text(HTML(f'Your signature (show this to companion):\n| <ansiyellow>{my_sign}</ansiyellow>\n'))
        print_formatted_text(HTML(f'Companion signature (сheck for correctness):\n| <ansiyellow>{companion_sign}</ansiyellow>\n'))
        ret = answer(f"Is the companion signature correct?")
        print()
        console_status.start()
        return ret

    # Настроен и готов к получению и передаче сообщений
    def on_ready(self):
        global ON_READY
        ON_READY = True

    # Таймаут при пинге
    def on_ping_timeout(self):
        console_status.stop()
        print_formatted_text(HTML(f'<ansired>Companion is unreachable. Ping timeout</ansired>'))
        clayer.stop()
        sys.exit()

    # Собеседник сообщил об отключении
    def on_disconnect(self):
        console_status.stop()
        print_formatted_text(HTML(f'<ansired>Companion decided to disconnect</ansired>'))
        clayer.stop(send_disconnect=False)
        sys.exit()


# Для вопросов
def answer(text, yes_default=False):
    if yes_default:
        user_input = pt_session.prompt(
            HTML(f"{text} (y/N): ")
        ).strip().lower()
        if not user_input:
            return True
    else:
        user_input = pt_session.prompt(
            HTML(f"{text} (y/N): ")
        ).strip().lower()
        if not user_input:
            return False

    if user_input in ["yes", "y"]:
        return True
    else:
        return False


# Для ошибок
def error(text):
    print_formatted_text(HTML(f'<ansired>{text}</ansired>'))


# Инциализация логирования
def init_logger():

    global LOGGER

    log_format = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s -> %(funcName)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()

    # вывод логов в файл
    if LOGS_TO_FILE:
        file_handler = logging.FileHandler(
            LOGS_FILE_PATH, encoding="utf-8", mode="w"
        )
        file_handler.setFormatter(log_format)
        root_logger.addHandler(file_handler)

    # вывод логов в терминал
    if PRINT_LOGS:
        terminal_handler = logging.StreamHandler(sys.stdout)
        terminal_handler.setFormatter(log_format)
        root_logger.addHandler(terminal_handler)

    LOGGER = logging.getLogger(f"{__file__}.{__name__}")


def init_module():

    global MODULE_CLASS

    module_manager.load()

    modules = module_manager.get_modules()

    print(f'\n - - Modules - -\n')
    for n, module in enumerate(modules):
        for name, desc in module.items():
            print_formatted_text(HTML(f"{n+1}. <ansiyellow>{name}</ansiyellow>: {desc}"))

    print()

    while True:
        selected_index = input(f'Choice module: {Fore.GREEN}').strip()
        print(ColoramaStyle.RESET_ALL, end="")

        if not selected_index.isdigit():
            error("Enter a number!")
            continue

        selected_index = int(selected_index) - 1

        if selected_index >= 0 and selected_index < len(modules):
            MODULE_CLASS = module_manager.get_module_by_index(selected_index)
            break
        else:
            error("Selected messenger does not exist!")
            continue


    credentials = MODULE_CLASS.get_creds()


    creds = []
    print(f'\n - - Credentials - -\n')
    for n, cred in enumerate(credentials):
        for name, desc in cred.items():
            if len(credentials) > 1:
                print(f"{n+1}. {Fore.YELLOW}{name}{ColoramaStyle.RESET_ALL}: {desc}")
            else:
                print(f"{Fore.YELLOW}{name}{ColoramaStyle.RESET_ALL}: {desc}")
            user_cred = getpass.getpass(f'{Fore.YELLOW}{name}{ColoramaStyle.RESET_ALL}: ').strip()
            creds.append(user_cred)
            print()


    compan_id = input(f"Companion ID (in module): {Fore.GREEN}").strip()
    print(ColoramaStyle.RESET_ALL, end="")

    print()

    MODULE_CLASS.init(creds, compan_id)



def main():

    global clayer

    password = getpass.getpass(f"Password (for CryptoLayer file encryption): ")

    init_logger()

    init_module()

    ui = TerminalUI()

    clayer = CryptoLayer(ui, DATA_DIR, MODULE_CLASS, password)

    del password

    clayer.init()



    while not ON_READY:
        time.sleep(0.5)

    try:

        print("\n - - - - - -\n")

        while True:

            with patch_stdout():
                user_input = pt_session.prompt(HTML('<ansigreen>you></ansigreen> ')).strip()

            if user_input == ":":
                if not answer("<ansired>You want send this?</ansired>"):
                    # sender_console()
                    continue

            clayer.send(user_input)

    except KeyboardInterrupt:
        print("\n - - - - - -\n")
        clayer.stop()



if __name__ == "__main__":
    main()
