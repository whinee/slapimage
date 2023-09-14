import itertools
import os
import re
import shutil
from typing import Any

import toml
from whinesnips.utils.cfg import dcfg, pcfg, rcfg
from whinesnips.utils.utils import inmd

from .vars import GLOBAL_VARS, LOCAL_VARS, YML

# Initialize Variables
MATRIX = {}
GLOBAL = {}
LOCAL = {}

# Constants
RE_MX = r"(?<=\{matrix.)[a-zA-Z0-9-_]+?(?=\})"

# Derived Constants
RE_PTSE = r"(?<=# \[DO NOT MODIFY\] {key} start\n).+(?=\n\s*# {key} end)"
VYML = rcfg("version.yml")

VLS = VYML["ls"]

VER_DIR = f"dev/constants/version/{VLS[0]}/{VLS[1]}"

SCRIPTS = rcfg(f"{VER_DIR}/scripts/meta.yml")

for k, v in SCRIPTS["matrix"].items():
    MATRIX[k] = [str(i) for i in v]

for k, v in dict(GLOBAL_VARS, **SCRIPTS["variables"]["global"] or {}).items():
    GLOBAL[k] = str(v)

for k, v in dict(LOCAL_VARS, **SCRIPTS["variables"]["local"] or {}).items():
    LOCAL[k] = str(v)


def mx_keys_combi(mx_keys: list[str]) -> list[dict[str, str]]:
    """
    Given list of matrix keys, fetch their values, then output a permutation of key-value pairs.

    Args:
    - mx_keys (`list[str]`): List of matrix keys.

    Returns:
    `list[dict[str, str]]`: Permutation of matrix key-value pairs.
    """
    op = []
    kls = [MATRIX[i] for i in mx_keys]
    for i in itertools.product(*kls):
        op.append(dict(zip(mx_keys, i, strict=True)))
    return op


def repl(name: str, path: str, op_path: str) -> tuple[str, str]:
    """
    Given a script's name, path, and output path, substitute the variables with its corresponding value.

    Args:
    - name (`str`): Script's name.
    - path (`str`): Script's path.
    - op_path (`str`): Script's output path.

    Returns:
    `tuple[str, str]`: Evaluated output path and file content.
    """
    lv = SCRIPTS.dir(f"variables/local/{name}", {})
    rmvg = {**GLOBAL, **lv}

    for k, v in rmvg.items():
        path = path.replace("{{" + k + "}}", v)
        op_path = op_path.replace("{{" + k + "}}", v)

    with open(path) as f:
        contents = f.read()

    for k, v in rmvg.items():
        contents = contents.replace("{{" + k + "}}", v)

    return op_path, contents


def mr(name: str, script_md: dict[str, str]) -> list[list[str]]:
    """
    Given a script's name and its corresponding metadata, check whether if the output file path contains a matrix. If so, the function should return a list of lists containing the output file path and the matrix output. Otherwise, just return a list containing a singular list of the file path of the script and its contents.

    The file contents are also evaluated for any variables and substituted with the appropriate values.

    Args:
    - name (`str`): script name.
    - script_md (`dict[str, str]`): script's metadata.

    Returns:
    `list[list[str]]`: Matrix output.
    """

    path, contents = repl(
        name,
        os.path.join(VER_DIR, "scripts", "tpl", script_md["path"]),
        script_md["op_path"],
    )
    if mx_keys := re.findall(RE_MX, path):
        op = []
        for i in mx_keys_combi(mx_keys):
            _path = path.copy()
            _contents = contents.copy()
            for k, v in i.items():
                _path = _path.replace("{{matrix." + k + "}}", v)
                _contents = _contents.replace("{{matrix." + k + "}}", v)
            op.append([_path, _contents])
        return op
    return [[path, contents]]


def info_tpls_filler(
    info_tpls_dict: dict[str, tuple[None, list[str]] | tuple[str, list[str]]],
) -> dict[str, Any]:
    """key-value pair of key and tuple with two items, the first item being the string template and the second being list of keys indexed from global variables to be placed in the string format. If the string format is `None`, then the values of the global variables indexed will be concatenated."""
    info_dict = {}
    for k, (str_fmt, kls) in info_tpls_dict.items():
        vd = {i: GLOBAL_VARS.dir(i, "None") for i in kls}
        if str_fmt is None:
            op = " ".join([str(i) for i in vd.values()])
        else:
            op = str_fmt.format(*vd.values(), **vd)
        info_dict[k] = op
    return info_dict


def key_repl(dict_key_repl: dict[str, str | Any], text: str) -> str:
    for key, repl_str in dict_key_repl.items():
        if isinstance(repl_str, str):
            typed_repl_str = repl_str
        else:
            typed_repl_str = toml.dumps(repl_str).rstrip()
        text = re.sub(
            RE_PTSE.format(key=key),
            typed_repl_str,
            text,
            0,
            re.S,
        )
    return text


def mod_justfile() -> None:
    shutil.copy("justfile", "justfile.bak")
    with open("justfile") as f:
        justfile = f.read()

    with open("justfile", "w") as f:
        f.write(
            key_repl(
                {
                    "src": f'src := "{YML.dir("files/project")}"',
                },
                justfile,
            ),
        )


def mod_pyproject() -> None:
    project_dir = YML.dir("files/project")
    info_tpls: dict[str, tuple[None, list[str]] | tuple[str, list[str]]] = {
        "name": (None, ["project/name" if project_dir == "src" else "project/pip"]),
        "license": (None, ["license_type"]),
        "version": (None, ["ver"]),
        "description": (None, ["text/desc"]),
        "homepage": ("https://{}", ["site"]),
        "repository": (
            "https://github.com/{}/{}",
            ["github/organization", "github/repo_name"],
        ),
        "documentation": ("https://{}", ["site"]),
    }

    info_authors_vd = {
        i: GLOBAL_VARS.dir(i, "None") for i in ["author/name_clean", "author/email"]
    }
    info_author = '    "{} <{}>",'.format(*info_authors_vd.values(), **info_authors_vd)

    info_dict: dict[str, Any] = {
        "readme": f'{YML.dir("docs/op")}/README.md',
        **info_tpls_filler(info_tpls),
    }

    shutil.copy("pyproject.toml", "pyproject.bak.toml")
    with open("pyproject.toml") as f:
        pyproject_toml = f.read()

    with open("pyproject.toml", "w") as f:
        f.write(
            key_repl(
                {
                    "info": info_dict,
                    "main author": info_author,
                    "main maintainer": info_author,
                    "package include source": '    { include = "' + project_dir + '" }',
                },
                pyproject_toml,
            ),
        )


def mod_files() -> None:
    mod_justfile()
    mod_pyproject()


def main() -> None:
    """Generate scripts from file templates."""

    mod_files()

    for name, script_md in (SCRIPTS["scripts"] or {}).items():
        for path, contents in mr(name, script_md):
            with open(inmd(path), "w") as f:
                if og_ext := script_md.get("og_ext"):
                    if ext := script_md.get("ext"):
                        contents = dcfg(pcfg(contents, og_ext), ext)
                f.write(contents)
