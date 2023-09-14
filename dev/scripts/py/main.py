import os
import re
from typing import Any, Optional

import inquirer
from whinesnips.utils.cfg import rcfg, wcfg
from whinesnips.utils.utils import run_cmd, vls_str

from . import scripts
from .vars import GLOBAL_VARS, MD_RULES_VARS, VYML, YML, vrcfg

# Constants
VERSIONS_NAME = [
    "User",
    "Dev",
    "Minor",
    "Patch",
    "Pre-release identifier",
    "Pre-release version",
]
DE_PUSH_MSG = "For info, check `docs/latest commit.md` or this commit's comments"
PUSH_CMD = 'git commit -am "{}"'
RE_MOD_DS = r"(def {}\(.*?:\s*?\n(\s+)(([\'\"])\4\4)).+?(?=\s*(?:Args:|Returns:|Raises:|Yields:|\3))"

# First Dependents
VLS = VYML["ls"]
VER_DIR = ["dev", "constants", "version", *[str(_) for _ in VLS[0:2]]]


# Derived Constants
VLS_STR_RE = re.compile(r"^(((0|[1-9][0-9]*) ){4}([0-2] (0|[1-9][0-9]*)|3 0))$")
PROJECT_CFG = vrcfg("project")
INIT_FILE = PROJECT_CFG["init_file"]
GLOBAL = MD_RULES_VARS["vars"]["global"]


def gdf() -> None:
    """Generate dynamic files."""
    scripts.main()

    const_dir = PROJECT_CFG["const_dir"]
    PROJECT_CFG["lang_dir"].format(const_dir=const_dir)

    for k, v in PROJECT_CFG["cp"].items():
        wcfg(f'{v["dir"].format(const_dir=const_dir)}.{v.get("ext", "mp")}', vrcfg(k))

    # for projects that require config files
    # cf_tpl = vrcfg("config")
    # Config(cf_tpl["version"])(cf_tpl["config"], const_dir)

    # NOTE: for projects that requirs i18n or uses language files
    # for i in list(Path(path.join(*VER_DIR, "lang")).rglob("*[!.test].yml")):
    #     tl_yml = CustomDict()

    #     for k, v in rcfg(i)["text"].items():
    #         for vk, vv in v.items():
    #             for vvk, vvv in vv.items():
    #                 tl_yml.modify("/".join([k, vk, vvk]), vvv["str"])

    #     wcfg(path.join(lang_path, path.splitext(path.basename(i))[0] + ".mp"), tl_yml)

    wcfg(os.path.join(YML.dir("files/project"), const_dir, "const.mp"), GLOBAL_VARS)


def docs() -> None:
    from .docs import main

    gdf()
    main()


def push(v: Optional[list[int]] = None) -> None:
    """
    Push changes to the remote repository. Pass version list of numbers to add.

    Args:
    - v (`list[int]`, optional): _description_. Defaults to `None`.
    """
    msg = inquirer.text(message="Enter commit message", default="push")

    docs()
    run_cmd("just lint")
    run_cmd("git add .")

    if v:
        msg = "\n".join(
            [
                "VERSION BUMP: ",
                msg,
                f"Release notes: https://{GLOBAL['site']}/changelog#{'-'.join([str(i) for i in v])} or `docs/latest release notes.md`",
            ],
        )

    run_cmd(PUSH_CMD.format(msg))
    run_cmd("git push")


def dcomp(x: int) -> list[int]:
    """
    Given a number x, return a list of times a prime factor of x occured.

    Args:
        x (int): Number to get the prime factors of.

    Returns:
        list[int]: List of times a prime factor of x occured.
    """
    primes = [3, 2]
    factors = [0 for _ in primes]
    while x != 1:
        for idx, i in enumerate(primes):
            if x % i == 0:
                factors[idx] += 1
                x = int(x / i)
                break
            pass
    return factors


def _set_ver(vls: list[int]) -> None:
    """
    Set version, and write to file.

    Args:
        vls (list[int]): Version list.
    """
    const_path = os.path.join(
        YML.dir("files/project"),
        PROJECT_CFG["const_dir"],
        "const.mp",
    )
    const_mp = rcfg(const_path)
    op_ls = [vls, *vls_str(vls)]

    wcfg("version.yml", dict(zip(["ls", "str", "sv"], op_ls, strict=True)))
    for k, v in zip(["vls", "__version__", "hver"], op_ls, strict=True):
        const_mp[k] = v
    wcfg(const_path, const_mp)


def vfn(answers: list[Any], current: str) -> bool:
    """
    Validation Function for version bump prompt. Check if given string to the prompt matches the regex for version.

    Args:
    - answers (`list[Any]`): Unused, list of answers from the previous prompts.
    - current (`str`): Current answer to the prompt.

    Raises:
    - `Exception`: If the given string to the prompt does not match the regex for version.

    Returns:
    `bool`: True, if the given string to the prompt matches the regex for version.
    """

    vlsr_match = VLS_STR_RE.match(current)

    if vlsr_match is None:
        raise Exception("Invalid version digits")

    x, y = vlsr_match.span()
    vls = current[x:y].strip().split(" ")
    if len(vls) == 6:
        _set_ver([int(i) for i in vls])
        return True

    raise Exception("Invalid version digits")


def vlir(idx: int, vls: list[int]) -> list[int]:
    """
    Version Lower than Index will be Reset.

    Args:
        idx (int): Index to compare to.
        vls (list[int], optional): Version list.

    Returns:
        list[int]: Modified version list.
    """

    for i in range(idx + 1, len(vls)):
        if i == 4:
            vls[i] = 3
        else:
            vls[i] = 0
    return vls


def _bump(idx: int) -> list[int]:
    """
    Bump's inner function. Given the index of the version part to bump, bump the said part and output that.

    Args:
        idx (int): Index to bump.

    Returns:
        list[int]: Modified version list.
    """

    _vls = list(VLS)
    if idx == 4:
        if _vls[idx] == 3:
            _vls[3] += 1
            _vls[4] = _vls[5] = 0
        else:
            _vls = vlir(idx, _vls)
            _vls[idx] += 1
    else:
        _vls = vlir(idx, _vls)
        _vls[idx] += 1
    return _vls


def bump() -> None:
    """Bump program's version."""
    while True:
        choices = []
        for idx, k in enumerate(VERSIONS_NAME):
            choices.append(f"{k.ljust(23)}(bump to {vls_str(_bump(idx))[0]})")
        choice = inquirer.list_input(
            message=f"What version do you want to bump? (Current version: {vls_str(VLS)[0]})",
            choices=choices,
        )
        idx = choices.index(choice)
        _vls = _bump(idx)
        print(
            f"    This will bump the version from {vls_str(VLS)[0]} to {vls_str(_vls)[0]} ({VERSIONS_NAME[idx]} bump). ",
        )
        match inquirer.list_input(
            message="Are you sure?",
            choices=[
                "Yes",
                "No",
                "Cancel",
            ],
        ):
            case "Yes":
                _set_ver(_vls)
                run_cmd(
                    f'python -c "from dev.scripts.py.main import push;push({_vls})"',
                )
                return
            case "No":
                continue
            case "Cancel":
                break
            case _:
                pass


def main(choice: Optional[str] = None) -> None:
    """
    Main function.

    Args:
    - choice (`str`, optional): Subcommand to run. Leave empty to prompt the user. Defaults to `None`.
    """

    if choice is None:
        choice = inquirer.list_input(
            message="What action do you want to take",
            choices=[
                ["Generate documentation", "docs"],
                ["Push to github", "push"],
                ["Bump a version", "bump"],
                ["Generate dynamic files", "gdf"],
                ["Set the version manually", "set_ver"],
            ],
        )

    match choice:
        case "docs":
            docs()
        case "push":
            push()
        case "bump":
            bump()
        case "gdf":
            gdf()
        case "set_ver":
            inquirer.text(
                message="Enter version digits seperated by spaces",
                validate=vfn,
            )
