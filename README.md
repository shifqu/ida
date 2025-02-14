# I Do Accountancy
A python app that takes care of your accountancy.

---
[![Code style: Ruff](https://img.shields.io/badge/style-ruff-41B5BE)](https://github.com/astral-sh/ruff)
[![Typing: Pyright](https://img.shields.io/badge/typing-pyright-%236a5acd
)](https://github.com/RobertCraigie/pyright-python)
[![License](https://img.shields.io/github/license/mashape/apistatus.svg)](https://opensource.org/license/mit)

---
## System requirements
I Do Accountancy uses [Python 3.12](https://www.python.org/downloads/).

Optionally Docker can be used for deployments or consistent local development.

##### Tip: The recommended IDE is [VSCode](https://code.visualstudio.com/). A `.vscode` directory is provided with a file containing recommended extensions alongside default launch configurations and workspace specific settings.

## Prerequisites
The builtin module [venv](https://docs.python.org/3/library/venv.html) is used to manage virtual environments, [pip-tools](https://github.com/jazzband/pip-tools?tab=readme-ov-file#pip-tools--pip-compile--pip-sync) to manage dependencies and [setuptools](https://setuptools.pypa.io/en/latest/) to build the actual project. A [compose file](https://docs.docker.com/reference/compose-file/) alongside a [Dockerfile](https://docs.docker.com/reference/dockerfile/) are also included.
### Create a virtual environment
`python -m venv .venv/`
### Activate the virtual environment
`source .venv/bin/activate`
### Ensure pip is updated and pip-tools is installed
`pip install --upgrade pip pip-tools`

## Installation
`pip-sync` is used to ensure only the required dependencies are installed. Without it, if any packages were installed before, they would remain in the environment.

`pip install` is used to ensure scripts are installed and available.
For development, the `--editable` flag is used in order to reflect changes made to the source code immediately. 

### Development
```
pip-sync requirements/dev.txt && \
pip install --editable .[dev]
```
### Production
```
pip-sync requirements/main.txt && \
pip install .
```

## Useful commands
### Format the source code and the tests
Formatting should likely be done as a last step as some auto-fixed linting issues can result in wrongly formatted code.
```
ruff format src/ tests/
```

### Lint the source code (and auto-fix what can be fixed)
```
ruff check --fix src/
pylint src/
```

###### Note: `&& \` to combine the command is not used because pylint should be ran regardless of the exit_code of ruff

### Type-check the source code
```
pyright src/
```

### Test the source code and generating an html report
```
pytest -s --cov=src/ --cov-report=term-missing --cov-report html tests/
```

### Docker
#### Rebuild, recreate the application and run it in the background
```
docker compose up -d --build --force-recreate
```

#### Check the container's logs (-f follows)
```
docker compose logs -f
```

#### Get a shell in the docker container
```
docker compose exec ida bash
```

## Contributing / Developing
### Update/Add/Compile requirements
Core dependencies should be added to `requirements/main.in` and development dependencies to `requirements/dev.in`.

Once this is done, `pip-compile` is used to generate the effective `requirements` files.

#### Development dependencies
```
pip-compile --extra dev -o requirements/dev.txt pyproject.toml
```

#### Main dependencies
```
pip-compile -o requirements/main.txt pyproject.toml
```

## Deploying
### Docker
#### Development
```
docker compose -f compose.yml -f compose.dev.yml up -d --build
```

#### Production
```
docker compose up -d --build
```

A compose file and Dockerfile are provided to deploy consistently. The files can be included in central compose files using the `include` directive in the central file. This is useful when deploying multiple services on a single server behind an nginx proxy. The central file would define the nginx config and just include this service.

---
