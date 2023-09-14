# regex to match recipe names and their comments:
# ^    (?P<recipe>\S+)(?P<args>(?:\s[^#\s]+)*)(?:\s+# (?P<docs>.+))*

# Constants
purple_msg := '\e[38;2;151;120;211m%s\e[0m'
time_msg := '\e[38;2;151;120;211m%s\e[0m: %.2fs\n'
# [DO NOT MODIFY] src start
src := "slapimage"
# src end

# Derived Constants
cwd := `python -c 'import os;print(os.getcwd())'`
system_python := if os_family() == "windows" { "py.exe -3.11" } else { "python3.11" }
pyenv_dir := cwd + if os_family() == "windows" { "\\pyenv" } else { "/pyenv" }
pyenv_bin_dir := pyenv_dir + if os_family() == "windows" { "\\Scripts" } else { "/bin" }
python := pyenv_bin_dir + if os_family() == "windows" { "\\python.exe" } else { "/python3" }
pyenv_activate := pyenv_bin_dir + if os_family() == "windows" { "\\Activate.ps1" } else { "/activate" }

# Choose recipes
default:
    @ just -lu; printf '%s ' press Enter to continue; read; just --choose

# n1 - n2
[private]
minus n1 n2:
    @ python -c 'print(round({{n1}} - {{n2}}, 2))'

# Time commands
[private]
time msg err *cmd:
    #!/usr/bin/env bash
    printf '{{purple_msg}}: ' 'cmd'; printf '%s ' {{cmd}}; echo
    cs=$(date +%s.%N)
    if {{cmd}}; then
        printf '{{time_msg}}' '{{msg}}' "$(just minus $(date +%s.%N) $cs)"
    else
        printf '{{time_msg}}' '{{err}}' "$(just minus $(date +%s.%N) $cs)"
    fi

# Time commands without saying command name
[private]
time_nc msg err *cmd:
    #!/usr/bin/env bash
    cs=$(date +%s.%N)
    if {{cmd}}; then
        printf '{{time_msg}}' '{{msg}}' "$(just minus $(date +%s.%N) $cs)"
    else
        printf '{{time_msg}}' '{{err}}' "$(just minus $(date +%s.%N) $cs)"
    fi

[private]
[unix]
b64e file:
    base64 -w0 {{file}}

# Run Menu Commands
[private]
menu cmd:
    @ just time_nc '{{cmd}}' '{{cmd}} failed' {{python}} -c "\"from dev.scripts.py.main import main;main('{{cmd}}')\""

# Run Without Time
[private]
menu_wt cmd:
    @ {{python}} -c "\"from dev.scripts.py.main import main;main('{{cmd}}')\""

[private]
nio_dev:
    @ {{ python }} -m no_implicit_optional dev; exit 0

[private]
nio_src:
    @ {{ python }} -m no_implicit_optional {{ src }}; exit 0

[private]
nio_test:
    @ {{ python }} -m no_implicit_optional test; exit 0

[private]
ruff:
    @ {{ python }} -m ruff check dev/scripts/py --fix
    @ {{ python }} -m ruff check {{ src }} --fix
    @ {{ python }} -m ruff check test --fix
    @ exit 0

# Set up development environment
bootstrap:
    #!/usr/bin/env bash
    rm -rf poetry.lock
    if test ! -e pyenv; then
        {{ system_python }} -m venv pyenv
        source {{pyenv_activate}}
    fi
    {{ python }} -m pip install --upgrade pip
    {{ python }} -m pip install mkdocs mkdocs-material mkdocs-minify-plugin mkdocs-redirects poetry
    {{ python }} -m poetry install --with dev

[private]
dev_prompt:
    @ echo Run the following command every time you open the terminal:;echo

# Activate development environment
[windows]
dev: dev_prompt
    @ cat dev/constants/dev/init-win.txt;echo

# Activate development environment
[linux]
[unix]
dev: dev_prompt
    @ cat dev/constants/dev/init-linux.txt;echo

# Activate development environment
[macos]
dev: dev_prompt
    @ cat dev/constants/dev/init-mac.txt;echo


# Generate documentation
docs:
    just menu "docs"

# Get program's version
ver: (menu "ver")

# Set the version manually
set_ver: (menu "set_ver")

# Bump version
bump: (menu "bump")

# Push to Github
push: (menu "push")

# Generate Dynamic Files
gdf: (menu "gdf")

# Lint codebase
lint:
    @ just time "     no_implicit_optional in dev" "     no_implicit_optional Failed" just nio_dev
    @ just time "     no_implicit_optional in src" "     no_implicit_optional Failed" just nio_src
    @ just time "    no_implicit_optional in test" "     no_implicit_optional Failed" just nio_test
    @ just time "        Markdown Files Formatted" "Formatting Markdown Files Failed" {{ python }} -m mdformat docs
    @ just time "          Python Files Formatted" "  Formatting Python Files Failed" {{ python }} -m black -q .
    @ just time "             Python Files Linted" "     Linting Python Files Failed" just ruff

# Build
build:
    rm -rf dist
    just gdf
    just docs
    just lint
    poetry build
