# Python scripts for maven project UT coverage and call chain generation

## Usage

clone repository in project root:

```bash
git clone git@github.com:Wakotu/maven_utcov.git scripts
```

python environment setup

```bash
python -m venv venv
source venv/bin/activate
cat scripts/requirements.txt | xargs -n 1 pip install
```

collecting coverage:

```bash
python scripts/get_test_methods.py
python scripts/run_cov.py
```

### Generating call chain

```bash
./scripts/get_callgraph.sh
python scripts/extract_callgraph.py
```

> [!NOTE]
> `./scripts/get_callgraph.sh` needs the `test-jar` goal specified in the package lifecycle. Please refer to [create_test_jar](https://maven.apache.org/plugins/maven-jar-plugin/examples/create-test-jar.html)  

customize the value for `PROJECT_PREFIX`:

```python
PROJECT_PREFIX = "org.apache.commons.lang3"
```
