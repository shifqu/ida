# I Do Accountancy
A python app that takes care of your accountancy.

---
[![Code style: Ruff](https://img.shields.io/badge/style-ruff-8b5000)](https://github.com/astral-sh/ruff)
[![Typing: Pyright](https://img.shields.io/badge/typing-pyright-725a42
)](https://github.com/RobertCraigie/pyright-python)
[![Dependencies: Pip-tools](https://img.shields.io/badge/dependencies-pip--tools-58633a
)](https://github.com/jazzband/pip-tools)
[![Framework: Django](https://img.shields.io/badge/framework-django-727242)](https://docs.djangoproject.com/en/5.1/)
[![CI Validation](https://github.com/shifqu/ida/actions/workflows/ci.yml/badge.svg)](https://github.com/shifqu/ida/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/mashape/apistatus.svg)](https://opensource.org/license/mit)

---
## System requirements
I Do Accountancy uses [Python 3.13](https://www.python.org/downloads/).

Optionally Docker can be used for deployments or consistent local development.

##### Tip: The recommended IDE is [VSCode](https://code.visualstudio.com/). A `.vscode` directory is provided with a file containing recommended extensions alongside default launch configurations and workspace specific settings.

## Prerequisites
The builtin module [venv](https://docs.python.org/3/library/venv.html) is used to manage virtual environments, [pip-tools](https://github.com/jazzband/pip-tools?tab=readme-ov-file#pip-tools--pip-compile--pip-sync) to manage dependencies and [setuptools](https://setuptools.pypa.io/en/latest/) to build the actual project. A [compose file](https://docs.docker.com/reference/compose-file/) alongside a [Dockerfile](https://docs.docker.com/reference/dockerfile/) are also included.
### Create a virtual environment
`python -m venv .venv/`
### Activate the virtual environment
#### UNIX
`source .venv/bin/activate`
#### WINDOWS
`.\.venv\Scripts\activate`
### Ensure pip is updated and pip-tools is installed
`python -m pip install --upgrade pip pip-tools`

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
ruff format src/
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

### Test the source code
```
manage test apps
```

### Coverage report for the source code
#### Run with coverage
```
coverage run -m manage test src/apps
```
#### Create the report
```
coverage report -m
```

### Combined commands for linting, formatting and type-checking
```
ruff check --fix src/
pylint src/
ruff format src/
pyright src/
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
docker compose exec ida /bin/sh
```

#### Remove all of the compose project's stuff
```
docker compose down -rmi all -v
```

#### Browse a volume in a temporary container (update VOLNAME with the correct volume name)
```
docker run --rm -it -v VOLNAME:/data alpine /bin/sh
```

### Django
#### Make migrations
```
manage makemigrations
```

#### Migrate
```
manage migrate
```
#### Reverse migrations (update APPNAME and 000N)
```
APPNAME="myapp" manage migrate $APPNAME 000N
```
##### This can be useful when you created many migrations during development, where some undo the previous and redo them. When done with development, you could just revert to the last migration on main, remove the new migrations on your branch and run makemigrations again.

#### Collect static files (not required when using runserver)
```
manage collectstatic
```

#### Add super-user
```
manage createsuperuser
```

#### Make translations
The following commands should be ran from the `apps` directory to avoid django attempting to create translations for non django apps.
```
cd src/apps
```

Initial command (include all locales you want to have generated)
```
manage makemessages --locale de --locale fr --locale nl
```

Later you probably just want to use --all and remove obsolete entries
```
manage makemessages --all --no-obsolete
```

The following command should be ran on fresh installs as the MO files are not included in version control.
```
manage compilemessages
```

#### Create app in the apps folder (update myapp as APPNAME)
##### Bash
```
APPNAME="myapp" bash -c 'mkdir -p src/apps/$APPNAME && manage startapp $APPNAME src/apps/$APPNAME'
```
##### Powershell
```
$env:APPNAME="myapp"; $ErrorActionPreference="Stop"; mkdir src\apps\$env:APPNAME; manage startapp $env:APPNAME src\apps\$env:APPNAME
```

#### Dump data for specific app (update myapp as APPNAME)
This could be useful to generate test-data
##### Bash
```
APPNAME="myapp" bash -c 'mkdir -p src/apps/$APPNAME/fixtures && manage dumpdata $APPNAME >> src/apps/$APPNAME/fixtures/$APPNAME.json'
```
###### Note: This appends to the file and thus, could result in duplicate pks. Older records are overwritten with newer records.

#### Generate a secret key
##### Bash
```
openssl rand -hex 40
```
##### Powershell
```
Add-Type -AssemblyName System.Web
[System.Web.Security.Membership]::GeneratePassword(81,0)
```

#### Run the development server (using 0.0.0.0 to be available to any device on the network)
```
manage runserver 0.0.0.0:38080
```

#### Set or update the telegram webhook (should be done only the first time the app is deployed)
```
manage setwebhook
```

## Contributing / Developing
### Update/Add/Compile requirements
Core dependencies should be added to `requirements/main.in` and development dependencies to `requirements/dev.in`.

Once this is done, `pip-compile` is used to generate the effective `requirements` files.

###### Note: To upgrade the dependencies, add `--upgrade` to the following commands

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

## FAQ
Q: After forking the repository, the workflows fail with the error `ida.environ.MissingEnvironmentVariableError: Environment variable DJANGO_SECRET_KEY is not set.`.
A: This is because IDA requires a secret to be set on the repository and secrets are not passed along to forks. Refer to [this URL](https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions?tool=webui#creating-secrets-for-a-repository) to learn how to create secrets for your repository.

---
