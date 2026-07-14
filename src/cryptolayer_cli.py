import os
import logging
import time
import sys
from datetime import datetime
import json

import getpass
from rich.console import Console
import colorama
from colorama import Fore, Style as ColoramaStyle
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit import HTML
from prompt_toolkit import print_formatted_text
from prompt_toolkit.styles import Style
from prompt_toolkit.application import get_app
from prompt_toolkit.key_binding import KeyBindings

from crypto_layer import CryptoLayer
from UIProvider import UIProvider

import module_manager
from base_module import BaseModule

import modules.hidden_imports

colorama.init()
pt_session = PromptSession()
console = Console()
console_status = console.status("...")

LOGGER = None
LOGS_TO_FILE = True
PRINT_LOGS = False

IS_FROZEN = getattr(sys, 'frozen', False)

if IS_FROZEN:
    REAL_EXEC_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    REAL_EXEC_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(REAL_EXEC_DIR, 'data')
LOGS_FILE_PATH = os.path.join(REAL_EXEC_DIR, 'crypto_layer.log')
WC_DICT_FILE_PATH = os.path.join(REAL_EXEC_DIR, 'wc_dict.json')

ON_READY = False

MODULE_CLASS = None

ALREADY_QUIT = False

clayer = None


class CustomPromptWrapper:
    def __init__(self, pt_session: PromptSession):
        self.session = pt_session
        self.input_finished = False
        self.last_timestamp = ""
        self.current_promt = f"<ansigreen>you  [{self.last_timestamp}]:</ansigreen> "

        self.kb = KeyBindings()

        @self.kb.add('enter')
        def _(event):
            user_text = event.current_buffer.text.strip()
            if user_text == ":":
                self.current_promt = f"<ansiyellow>you> </ansiyellow>"
            elif user_text == "":
                self.current_promt = f"<ansibrightblack>you> </ansibrightblack>"
            else:
                self.last_timestamp = datetime.now().strftime("%H:%M:%S")
                self.current_promt = f"<ansigreen>you  [{self.last_timestamp}]:</ansigreen> "
            self.input_finished = True
            event.app.invalidate()
            event.current_buffer.validate_and_handle()

    def get_prompt(self):
        if self.input_finished:
            return HTML(self.current_promt)
        return HTML('<ansigreen>you></ansigreen> ')

    def get_input(self):
        self.input_finished = False

        with patch_stdout():
            user_input = self.session.prompt(
                self.get_prompt,
                key_bindings=self.kb
            )
            return user_input.strip()



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
        quit_clayer_cli(send_disconnect=False)

    # Собеседник сообщил об отключении
    def on_disconnect(self):
        if not ALREADY_QUIT:
            console_status.stop()
            print_formatted_text(HTML(f'<ansired>Companion decided to disconnect</ansired>'))
            quit_clayer_cli(send_disconnect=False)


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


# Чтение JSON из файла
def load_json_to_dict(file_path):

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        # Проверяем, что на выходе именно словарь, а не список или строка
        if isinstance(data, dict):
            return data
        else:
            error(
                f"Data in '{file_path}' = {type(data).__name__}, but not dict"
            )
            return None

    except FileNotFoundError:
        error(f"File '{file_path}' not found!")
        return None
    except json.JSONDecodeError as e:
        error(f"File '{file_path}' contains not correct JSON ({e})")
        return None


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

    wc_dict = load_json_to_dict(WC_DICT_FILE_PATH)

    clayer = CryptoLayer(ui, DATA_DIR, MODULE_CLASS, password, wc_dict)

    del password

    clayer.init()



    while not ON_READY:
        time.sleep(0.5)

    try:

        prompt_manager = CustomPromptWrapper(pt_session)

        print("\n - - - - - -\n")

        while True:

            with patch_stdout():
                user_input = prompt_manager.get_input()

            if not user_input:
                continue

            if user_input == ":":
                if not answer("<ansired>Send this? (or open console)</ansired>"):
                    cmd()
                    continue
                else:
                    last_timestamp = datetime.now().strftime("%H:%M:%S")
                    print_formatted_text(HTML(f"<ansigreen>you  [{last_timestamp}]</ansigreen>: {user_input}"))

            clayer.send(user_input)

    except KeyboardInterrupt:
        quit_clayer_cli()


COMMANDS = {
        "q": "Quit CryptoLayer CLI",
        "b": "Back to chat",
}


def cmd():
    try:
        all_commands_text = "\n - - COMMANDS - - \n"
        for c in COMMANDS:
            all_commands_text += f"<ansiyellow>{c}</ansiyellow> - {COMMANDS[c]}\n"
        print_formatted_text(HTML(all_commands_text))
        while True:
            user_input = pt_session.prompt(HTML(f"<ansiyellow>CMD></ansiyellow> ")).strip().lower()

            if user_input == "q":
                quit_clayer_cli()

            elif user_input == "b":
                return

            elif user_input == "":
                continue

            else:
                error("Unknown command!\n")
                print_formatted_text(HTML(all_commands_text))
    except KeyboardInterrupt:
        return

def quit_clayer_cli(send_disconnect=True):
    global ALREADY_QUIT
    if not ALREADY_QUIT:
        ALREADY_QUIT = True
        console_status.start()
        print("\n - - - - - -\n")
        clayer.stop(send_disconnect)
        console_status.stop()
        os._exit(0)


if __name__ == "__main__":
    main()
