# Python scripts for maven project UT coverage

## Usage

clone repository in project root:

```bash
git clone git@github.com:Wakotu/maven_utcov.git scripts
```

python environment setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r scripts/requirements.txt
```

collecting coverage:

```bash
python scripts/get_test_methods.py
python scripts/run_cov.py
```
