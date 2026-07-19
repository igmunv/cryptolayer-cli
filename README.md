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



## Запуск проекта

```bash

git clone https://github.com/igmunv/CryptoLayer.git

cd CryptoLayer

./run.sh

```
или
```bash

git clone https://github.com/igmunv/CryptoLayer.git

cd CryptoLayer

git submodule update --init --recursive

python3 -m venv venv

source venv/bin/activate

pip install -r requirements.txt

cd src

python3 run.py

```

> [!TIP]
> Если вам необходимо просто использовать CryptoLayer CLI по назначению, то лучше посмотрите последний релиз и скачайте оттуда готовый бинарный файл
