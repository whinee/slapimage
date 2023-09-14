import base64
import glob
import os
import urllib.parse
from datetime import date

from whinesnips.cd import CustomDict, flatten_element
from whinesnips.utils.cfg import rcfg
from whinesnips.utils.utils import vls_str

# Constants
OP_CHOLDER_TPL = """by [{cholder}, Github account <a target=_blank
href="https://github.com/{user}">{user}</a> owner, {year}] as part of project
<a target=_blank href="https://github.com/{org}/{project}">{project}</a>"""

M_CHOLDER_TPL = """Copyright for portions of project <a target=_blank
href="https://github.com/{org}/{project}">{project}</a> are held {mc}.

All other copyright for project <a target=_blank
href="https://github.com/{org}/{project}">{project}</a> are held by [Github
Account <a target=_blank href="https://github.com/{user}">{user}</a> Owner, {year}]."""

S_CHOLDER_TPL = """Copyright (c) {year} Github Account <a target=_blank
href="https://github.com/{user}">{user}<a> Owner"""

PYTEST_BADGE_TPL = '<img src="https://img.shields.io/badge/PYTEST-{text}-{color}?style=for-the-badge&logoWidth=25&logo=data:image/png;base64,{icon}">'

COLORS = {
    "brightgreen": "#4c1",
    "green": "#97ca00",
    "yellowgreen": "#a4a61d",
    "yellow": "#dfb317",
    "orange": "#fe7d37",
    "red": "#e05d44",
    "lightgrey": "#9f9f9f",
}

# Derived Constants
VYML = rcfg("version.yml")
YML = rcfg("wh_dev.yml")

VLS = VYML["ls"]
FILES = YML["files"]
DOCS = YML["docs"]
LICENSE = YML["license"]
VARS = YML["vars"]

FILES_DEV_DIR = FILES["dev_dir"]
VER_DIR = os.path.join(
    FILES_DEV_DIR,
    FILES["constants_ver_dir"],
    *[str(_) for _ in VLS[0:2]],
)
DOCS_INPUT = DOCS["input"]
GLOBAL_VARS = VARS["global"]
LOCAL_VARS = VARS["local"]

PROJECT = GLOBAL_VARS["project"]
GITHUB = GLOBAL_VARS["github"]

PN = PROJECT["name"]
YEAR = PROJECT["year"]
ORG = GITHUB["organization"]
USER = GITHUB["user"]

# Initialize
cholder_ls = []


# Functions
def vrcfg(name: str) -> "CustomDict":
    """
    Read config from directory of current version's constants.

    Args:
    - name (`str`): Name of the config to read.

    Returns:
    `CustomDict`: Config.
    """
    return rcfg(os.path.join(VER_DIR, f"{name}.yml"))


if LICENSE["cholder"]:
    for c, mp in LICENSE["cholder"].items():
        user = mp.get("user", c)
        for org, projects in mp["projects"].items():
            for project, pm in projects.items():
                cholder_ls.append(
                    OP_CHOLDER_TPL.format(
                        cholder=c,
                        org=org,
                        project=project,
                        user=user,
                        year=pm["year"],
                    ),
                )
    if len(cholder_ls) > 1:
        cholder_ls[-2] += f", and {cholder_ls[-1]}"
        del cholder_ls[-1]
    cholder = M_CHOLDER_TPL.format(
        mc=", ".join(cholder_ls),
        org=ORG,
        project=PN,
        user=USER,
        year=YEAR,
    )
else:
    cholder = S_CHOLDER_TPL.format(user=USER, year=YEAR)


GLOBAL_VARS = CustomDict(
    {
        **GLOBAL_VARS,
        "year": str(date.today().year),
        "cholder": cholder,
        "license_type": LICENSE["type"],
    },
)

for k, v in zip(["vls", "ver", "sver"], [VLS, *vls_str(VLS)], strict=True):
    GLOBAL_VARS[k] = v

for idx, i in enumerate(["user", "dev", "minor", "patch", "pri", "prv"]):
    GLOBAL_VARS[f"ver_{i}"] = str(VLS[idx])

GLOBAL_VARS["text"] = {
    k: v["str"] for k, v in vrcfg("lang/en").dir("text/common/info").items()
}

VARS["global"] = GLOBAL_VARS

# Additional Global Variables for raw markdown
MD_GLOBAL_VARS = {**GLOBAL_VARS}

# current version directory
DOCS = YML["docs"]
MD_GLOBAL_VARS["ver_dir"] = ver_dir = os.path.join(DOCS["docs"], "version")
MD_GLOBAL_VARS["current_ver_dir"] = os.path.join(ver_dir, *(str(i) for i in VLS[:2]))

# .png icons in base64
for file_path in glob.glob(os.path.join(DOCS_INPUT, FILES["icons_dir"], "*.png")):
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    with open(file_path, "rb") as f:
        MD_GLOBAL_VARS["icons/png_b64_" + base_name] = base64.b64encode(
            f.read(),
        ).decode("utf-8")

# Pytest Badge
QS_NA = {
    "text": urllib.parse.quote("N/A"),
    "color": COLORS["lightgrey"][1:],
    "icon": MD_GLOBAL_VARS["icons/png_b64_issues"],
}

# with open("tmp/junit.xml") as f:  # type: ignore[assignment]
#     root = ET.fromstring(f.read())
#     testsuite = root.find("testsuite")
#     if testsuite is None:
#         qs = QS_NA.copy()
#     else:
#         data: dict[str, str | None] = {
#             "errors": testsuite.get("errors"),
#             "failures": testsuite.get("failures"),
#             "skipped": testsuite.get("skipped"),
#             "tests": testsuite.get("tests"),
#         }
#         if any(item is None for item in data.values()):
#             qs = QS_NA.copy()
#         else:
#             percentage = int(round((1 - (int(data["errors"]) / int(data["tests"]))) * 100, 0))  # type: ignore[arg-type]

#             if percentage >= 95:
#                 color = COLORS["brightgreen"]
#             elif percentage >= 90:
#                 color = COLORS["green"]
#             elif percentage >= 85:
#                 color = COLORS["yellowgreen"]
#             elif percentage >= 80:
#                 color = COLORS["yellow"]
#             elif percentage >= 75:
#                 color = COLORS["orange"]
#             else:
#                 color = COLORS["red"]

#             if percentage >= 95:
#                 icon = MD_GLOBAL_VARS["icons/png_b64_check"]
#                 state = "pass"
#             else:
#                 icon = MD_GLOBAL_VARS["icons/png_b64_cross"]
#                 state = "fail"

#             qs = {
#                 "text": urllib.parse.quote(f"{state} ({percentage}%)"),
#                 "color": color[1:],
#                 "icon": icon,
#             }
#     MD_GLOBAL_VARS["badges"]["pytest_img_tag"] = PYTEST_BADGE_TPL.format(**qs)

MD_RULES_VARS = CustomDict(
    {
        "rules": YML["rules"],
        "vars": {
            "global": flatten_element(MD_GLOBAL_VARS),
            "local": {k: flatten_element(v) in LOCAL_VARS.items()},
        },
    },
)
