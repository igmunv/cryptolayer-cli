import os
import sys
import importlib
import inspect

from base_module import BaseModule


MODULES_DIR_NAME = "modules"
MODULES = []


def get_modules_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, MODULES_DIR_NAME)
    return os.path.join(os.path.dirname(__file__), MODULES_DIR_NAME)


def load():


    modules_path = get_modules_path()

    if modules_path not in sys.path:
        sys.path.insert(0, modules_path)

    if not os.path.exists(modules_path):
        return


    for item in os.listdir(modules_path):
        item_path = os.path.join(modules_path, item)
        if os.path.isdir(item_path) and not item.startswith('_'):
            try:

                module = importlib.import_module(f"{item}.main")

                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseModule) and obj is not BaseModule:
                        main_class = obj()
                        MODULES.append(main_class)
            except Exception as e:
                pass


def get_modules():
    ret = []
    for module in MODULES:
        ret.append({module.name: module.description})
    return ret


def get_module_by_index(index):
    try:
        return MODULES[index]
    except Exception as e:
        return None
