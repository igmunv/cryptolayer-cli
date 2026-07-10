
git submodule update --init --recursive

python3 -m venv venv

source venv/bin/activate

python3 modules/generate_reqs.py

pip install -r modules/common_requirements.txt

pip install -r requirements.txt

cd src

python3 cryptolayer_cli.py
