import os
import logging
import time
import sys
from datetime import datetime
import json
import base64

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

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
CLI_DATA_DIR = os.path.join(DATA_DIR, 'cli')
LOGS_FILE_PATH = os.path.join(REAL_EXEC_DIR, 'crypto_layer.log')
WC_DICT_FILE_PATH = os.path.join(REAL_EXEC_DIR, 'wc_dict.json')

ON_READY = False

MODULE_CLASS = None

ALREADY_QUIT = False

clayer = None

PASSWORD = None


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
        global ALREADY_QUIT

        if ALREADY_QUIT:

            if status_type == "in_progress":
                print_formatted_text(HTML(f"[*] {stage}: <ansiyellow>{message}</ansiyellow>"))
            elif status_type == "error":
                print_formatted_text(HTML(f"[x] {stage}: <ansired>{message}</ansired>"))
            elif status_type == "success":
                print_formatted_text(HTML(f"[+] {stage}: <ansigreen>{message}</ansigreen>"))

        else:


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
            HTML(f"{text} (Y/n): ")
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
            return {}

    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        return {}


# Запись словаря в JSON-файл
def save_dict_to_json(data, file_path):

    # Проверяка что на входе словарь
    if not isinstance(data, dict):
        error(f"Data to save is {type(data).__name__}, but expected dict")
        return False

    try:
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        return True

    except TypeError as e:
        error(f"Data contains elements that cannot be serialized to JSON: {e}")
        return False
    except OSError as e:
        error(f"Could not write to file '{file_path}': {e}")
        return False


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

    module_uid = MODULE_CLASS.unique_id

    credentials = MODULE_CLASS.get_creds()


    CREDS = []
    print(f'\n - - Credentials - -\n')

    saved_credentials = load_credentials(module_uid)

    if saved_credentials:

        if answer("Do you want to choose a credentials from your saved list?", yes_default=True):

            print()

            for n, sc in enumerate(saved_credentials):
                print(f"{n+1}. {Fore.YELLOW}{sc}{ColoramaStyle.RESET_ALL}")

            print()

            sel_index = choice_index("Choice credentials", list(saved_credentials.items()))
            CREDS = list(saved_credentials.items())[sel_index][1]

            if len(CREDS) != len(credentials):
                error("The selected credentials do not meet the module requirements. Enter them manually")
                CREDS = None

    if not CREDS:

        for n, cred in enumerate(credentials):
            for name, desc in cred.items():
                if len(credentials) > 1:
                    print(f"{n+1}. {Fore.YELLOW}{name}{ColoramaStyle.RESET_ALL}: {desc}")
                else:
                    print(f"{Fore.YELLOW}{name}{ColoramaStyle.RESET_ALL}: {desc}")
                user_cred = getpass.getpass(f'{Fore.YELLOW}{name}{ColoramaStyle.RESET_ALL}: ').strip()
                CREDS.append(user_cred)
                print()

        if answer("Do you want to save this credentials?"):

            while True:
                CRED_NAME = input(f"Credentials name: {Fore.GREEN}").strip()
                print(ColoramaStyle.RESET_ALL, end="")
                if CRED_NAME:
                    if CRED_NAME not in list(saved_credentials.values()):
                        break
                    else:
                        error("A credentials with that name already exists!")
            saved_credentials[CRED_NAME] = CREDS
            save_credentials(saved_credentials, module_uid)

    print(f'\n - - Companion - -\n')

    saved_companions = load_json_to_dict(get_module_companions_file_path(module_uid))

    COMPAN_ID = None

    if saved_companions:

        if answer("Do you want to choose a companion from your saved list?", yes_default=True):

            print()

            for n, sc in enumerate(saved_companions):
                print(f"{n+1}. {Fore.YELLOW}{saved_companions.get(sc)}{ColoramaStyle.RESET_ALL}")

            print()

            sel_index = choice_index("Choice companion", list(saved_companions.items()))
            COMPAN_ID = list(saved_companions.keys())[sel_index]

    if not COMPAN_ID:
        COMPAN_ID = input(f"Companion ID (in module): {Fore.GREEN}").strip()
        print(ColoramaStyle.RESET_ALL, end="")

        if not saved_companions.get(COMPAN_ID):
            if answer("Do you want to save this companion?", yes_default=True):
                while True:
                    COMPAN_NAME = input(f"Companion name: {Fore.GREEN}").strip()
                    if COMPAN_NAME:
                        if COMPAN_NAME not in list(saved_companions.values()):
                            break
                        else:
                            error("A companion with that name already exists!")
                saved_companions[COMPAN_ID] = COMPAN_NAME
                save_dict_to_json(saved_companions, get_module_companions_file_path(module_uid))

    print()

    MODULE_CLASS.init(CREDS, COMPAN_ID)


def encrypt_to_base64(password: str, data: str) -> str:

    salt = os.urandom(16)
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=b"public-key-encryption",
    )

    key = hkdf.derive(password.encode())
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    encrypted_data = aesgcm.encrypt(nonce, data.encode(), associated_data=None)

    full_blob = salt + nonce + encrypted_data

    return base64.b64encode(full_blob).decode('utf-8')


def decrypt_from_base64(password: str, b64_data: str) -> str:
    raw_blob = base64.b64decode(b64_data)

    salt = raw_blob[:16]
    nonce = raw_blob[16:28]
    encrypted_data = raw_blob[28:]

    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=b"public-key-encryption",
    )
    key = hkdf.derive(password.encode())

    aesgcm = AESGCM(key)
    decrypted_bytes = aesgcm.decrypt(nonce, encrypted_data, associated_data=None)

    return decrypted_bytes.decode('utf-8')


def load_credentials(module_uid) -> dict:
    ready_creds = {}
    encrypt_creds = load_json_to_dict(get_module_credentials_file_path(module_uid))
    if encrypt_creds:
        for name in encrypt_creds:
            creds = encrypt_creds[name]
            ready_list = []
            for c in creds:
                ready_list.append(decrypt_from_base64(PASSWORD, c))
            ready_creds[name] = ready_list
    return ready_creds


def save_credentials(creds: dict, module_uid):
    ready_encrypt_creds = {}
    for name in creds:
        ready_list = []
        for c in creds[name]:
            ready_list.append(encrypt_to_base64(PASSWORD, c))
        ready_encrypt_creds[name] = ready_list

    save_dict_to_json(ready_encrypt_creds, get_module_credentials_file_path(module_uid))


def get_module_companions_file_path(uid):
    return os.path.join(CLI_DATA_DIR, f'companions_{uid}.json')

def get_module_credentials_file_path(uid):
    return os.path.join(CLI_DATA_DIR, f'credentials_{uid}.json')

def choice_index(prompt, array):
    while True:
        selected_index = input(f'{prompt}: {Fore.GREEN}').strip()
        print(ColoramaStyle.RESET_ALL, end="")

        if not selected_index.isdigit():
            error("Enter a number!")
            continue

        selected_index = int(selected_index) - 1

        if selected_index >= 0 and selected_index < len(array):
            return selected_index
        else:
            error("Selected index does not exist!")
            continue

def main():

    global clayer
    global PASSWORD

    os.makedirs(CLI_DATA_DIR, exist_ok=True)

    PASSWORD = getpass.getpass(f"Password (for CryptoLayer file encryption): ")

    init_logger()

    init_module()

    ui = TerminalUI()

    wc_dict = load_json_to_dict(WC_DICT_FILE_PATH)

    clayer = CryptoLayer(ui, DATA_DIR, MODULE_CLASS, PASSWORD, wc_dict)

    del PASSWORD

    clayer.init()



    while not ON_READY:
        time.sleep(0.5)

    try:

        prompt_manager = CustomPromptWrapper(pt_session)

        print("\n - - - - - -\n")

        while True:

            with patch_stdout():
                user_input = prompt_manager.get_input()

            if ALREADY_QUIT:
                break

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
        pass

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
        console_status.stop()
        clayer.stop(send_disconnect)
        os._exit(0)


if __name__ == "__main__":
    main()
