<div align="center">

<img src="docs/logo.svg" width="250" alt="CryptoLayer-CLI Logo">

<br>
<h3>CryptoLayer-CLI</h3>
<h6> Консольное приложение для безопасного общения в существующих мессенджерах использующее для этого библиотеку <a href="https://github.com/igmunv/cryptolayer">CryptoLayer</a></h6>

[![License](https://img.shields.io/badge/License-MIT-brightgreen?color=orange&style=flat-square)](LICENSE)
[![Contributions Welcome](https://img.shields.io/badge/Contributions-Welcome-brightgreen?style=flat-square)](CONTRIBUTING.md)
<br>
[![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54&style=flat-square)](https://www.python.org/)

</div>

<img width="1750" height="1850" alt="user12-clcli-ru" src="https://github.com/user-attachments/assets/0a9d5c70-5987-444f-8845-a58c9a9fc6e9" />

## 💬 Использование

1. **🔑 Авторизация:** Введите пароль для шифрования локальных файлов CryptoLayer.
2. **📖 Выбор словаря:** Укажите нужный словарь для работы **WordCoder**.
3. **🧩 Модуль:** Выберите модуль и введите данные для авторизации в канале связи.
4. **👤 Настройка чата:** Укажите идентификатор собеседника и убедитесь, что он тоже готов к подключению.
5. **🛡️ Установление связи:** Ожидайте, пока CryptoLayer создаст защищенный туннель.
6. **💬 Общение:** Безопасно переписывайтесь через шифрованный канал!


## 🚀 Запуск CryptoLayer CLI


> [!TIP]
> Если вы не разработчик, скачайте готовый исполняемый файл в [последнем релизе](https://github.com/igmunv/cryptolayer-cli/releases/latest).

```bash

git clone https://github.com/igmunv/cryptolayer-cli.git

cd cryptolayer-cli

./run.sh

```

или

```bash

git clone https://github.com/igmunv/cryptolayer-cli.git

cd cryptolayer-cli

git submodule update --init --recursive

python3 -m venv venv

source venv/bin/activate

python3 src/modules/generate_reqs.py

pip install -r src/modules/common_requirements.txt

pip install -r requirements.txt

python3 src/modules/generate_hidden_imports.py

cd src

python3 cryptolayer_cli.py

```
