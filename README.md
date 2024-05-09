# Python scripts for maven project UT coverage

## Usage

python environment setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

collecting coverage:

```bash
python scripts/get_test_methods.py
python scripts/run_cov.py
```
