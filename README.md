# api

Prism Backend implemented with FastAPi

## Setup

1. Create a new conda environment and install python 3.10

```bash
conda create -n prism
conda install python=3.10
```

2. Install poetry

```bash
curl -sSL https://install.python-poetry.org | python -
```

3. Install packages and activate the virtual environment

```bash
poetry install
poetry shell
```

4. Install packages from requirements.txt

```bash
pip install -r requirements.txt
```

5. Setup pre-commit git hook

```bash
pre-commit install
```

6. Run the api using the following command

```bash
cd app
python -m uvicorn main:app --workers 4 --reload
```

## Before committing

Run the following command

```bash
pre-commit run --all-files
```

## Adding new packages

Use the following command

```bash
poetry add [PACKAGE_NAME]
```

## ETC

### Delete **pycache**

```bash
find . | grep -E "(/__pycache__$|\.pyc$|\.pyo$)" | xargs rm -rf
```

### Delete local branches

```bash
git branch | grep -v "main" | xargs git branch -D
```
