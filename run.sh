
git submodule update --init --recursive

python3 -m venv venv

source venv/bin/activate

pip install -r requirements.txt

cd src

python3 run.py
