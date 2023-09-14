import json
import os
import re
import shutil
import textwrap
from collections.abc import Callable, Generator
from functools import partial
from io import StringIO
from os import listdir
from os.path import dirname as dn
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import frontmatter
import panflute
import pdoc
import pypandoc
import yaml
from mako.template import Template
from whinesnips import DEF_STR
from whinesnips.utils.utils import (
    cycle_2ls,
    inmd,
    noop,
    repl,
    run_cmd,
    run_mp,
    run_mp_star,
)

if TYPE_CHECKING:
    from whinesnips.cd import CustomDict

from .vars import GLOBAL_VARS, MD_RULES_VARS, VYML, YML

# Constants
HA_VNS = 2
HA_VNE = 11

MD_HEADER = """
<style>
ul{
  padding-left: 20px;
}
</style>
"""

AW = '<a href="#{id}">{content}</a>'  # A tag
HW = '<h{n} id="{id}">{title}</h{n}>\n'
HA_DEF_STYLE = "<b>{}</b>"  # Header All Default Style
HA_RSTYLE = [
    HA_DEF_STYLE,
    "<b><i>{}</i></b>",
    "{}",
    "<i>{}</i>",
]  # Header All Repeated Style
H1 = "---\ntitle: {title}\n---\n\n# **{header}**\n\n"
H1_STH = H1.format(title="{header}", header="{header}")  # h1 same title and header
H1_MD = H1 + "{md}\n"
H1_MD_STH = H1.format(title="{header}", header="{header}") + "{md}\n"
H1_LINK_MD = H1.format(header="[{title}]({link})", title="{title}") + "{md}\n"
H1_LINK_MD_STH = H1.format(header="[{header}]({link})", title="{header}") + "{md}\n"
LINK = "[{text}]({link})"

SUBMOD_HEADER_TPL = (
    '\n\n## **<a href="#sub" id="sub">Sub-modules</a>**\n\n{}\n'  # sub-module heading
)
SUPMOD_HEADER_TPL = '\n\n## **<a href="#super" id="super">Super-module</a>**\n- [{}](README.md)\n'  # sub-module heading

RE_MDSE_FMT = r"(?<=# \[DO NOT MODIFY\] {key} start\n).+(?=\n\s*# {key} end)"

INFO_TPLS: dict[str, tuple[None, list[str]] | tuple[str, list[str]]] = {
    "site_name": (None, ["project/name"]),
    "site_url": ("https://{}", ["site"]),
    "repo_url": (
        "https://github.com/{}/{}",
        ["github/organization", "github/repo_name"],
    ),
    "site_description": (None, ["text/desc"]),
    "site_author": (None, ["author/name"]),
    "copyright": ("Copyright &copy; {} {}", ["project/year", "author/name"]),
}

# Derived Constants
VAR_RE = re.compile(r"\{\{\w+\}\)}")
TITLE_WRAP = textwrap.TextWrapper(width=15)

VLS = VYML["ls"]

FILES = YML["files"]
PDOC = YML["pdoc"]
MAKO = YML["mako"]
DOCS = YML["docs"]

PROJECT_DIR = FILES["project"]

DOCS_INPUT: str = DOCS["input"]  # Docs Input Directory
DOCS_IP_DOCS = os.path.join(DOCS_INPUT, DOCS["docs"])  # Docs Input Docs Directory
DOCS_OP = DOCS["op"]  # Docs Output Directory
DOCS_OP_TMP = DOCS["op_tmp"]  # Docs Temporary Output Directory
DOCS_OP_SITE = DOCS["op_site"]  # Docs Site Output Directory
DOCS_OP_DOCS = os.path.join(DOCS_OP, DOCS["docs"])  # Docs Outpot Docs Directory
DOCS_IP_DOCS_VER = os.path.join(DOCS_IP_DOCS, "version")
DOCS_OP_DOCS_VER = os.path.join(DOCS_OP_DOCS, "version")

DIDV_PATH = Path(DOCS_IP_DOCS_VER)

MAKO_GEN = MAKO["gen"]

MKDOCS_MOD_DOCS = {"docs_dir": DOCS_OP_TMP, "site_dir": DOCS_OP_SITE}
with open("mkdocs.yml") as f:
    MKDOCS_YML = f.read()

HTI_RF = re.compile(r"[\s\d\w]+", re.MULTILINE | re.DOTALL | re.UNICODE).findall
TOMD_RS = partial(re.compile("-{2,}").sub, "-")

CONTEXT = pdoc.Context()
PROJECT = pdoc.Module(PROJECT_DIR, context=CONTEXT)
PNH = PROJECT.name  # project name header

pdoc.link_inheritance(CONTEXT)
pdoc.tpl_lookup = pdoc.TemplateLookup(directories=PDOC["tpl"])

H1_STYLE = HA_RSTYLE[0]

# Variable Initialization
HA_STYLE = {}


# Class Initialization
class Constants:
    pass


# Function Initialization
def str_presenter(dumper: yaml.Dumper, data: str) -> Any:
    if len(data.splitlines()) > 1:  # check for multiline string
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


# Last Initialization
TOC_H2A = H1_STYLE.format(AW.format(id="toc", content="Table of Contents"))
TOC_H2 = HW.format(n=2, id="toc", title=TOC_H2A)
hs = HA_VNS - 1
for i, j in cycle_2ls(range(HA_VNS, HA_VNE + 1), HA_RSTYLE):
    if j == H1_STYLE:
        hs += 1
    HA_STYLE[i] = [hs, j]

ld = -1

yaml.add_representer(str, str_presenter)


# Functions
def mkdocs_mod(key: str, repl_str: str | list[Any] | dict[str, Any]) -> None:
    global MKDOCS_YML

    if isinstance(repl_str, str):
        typed_repl_str = repl_str
    else:
        typed_repl_str = yaml.dump(repl_str, indent=2, sort_keys=False).rstrip()
    MKDOCS_YML = re.sub(
        RE_MDSE_FMT.format(key=key),
        typed_repl_str,
        MKDOCS_YML,
        0,
        re.S,
    )


def dd(
    od: dict[str, list[str]],
    *dicts: list[dict[str, list[str]]],
) -> dict[str, list[str]]:
    for d in dicts:
        if d is None:
            continue
        for a, v in d.items():
            od[a] = [*(od.get(a, []) or []), *v]
    return od


def pdoc_dir(mn: str, rel: bool = False) -> str:
    """mn: module name."""
    mls = mn.split(".")
    if PROJECT_DIR == mls[0]:
        if len(mls) == 1:
            mls[0] = "README"
        elif len(mls) >= 2:
            del mls[0]

    rel_path = os.path.join(
        *mls[:-1],
        f"{mls[-1]}.md",
    )

    abs_path = os.path.join(
        DOCS_OP_DOCS_VER,
        *[str(i) for i in VLS[0:2]],
        "api",
        rel_path,
    )

    inmd(abs_path)

    if rel:
        return rel_path
    return abs_path


def elem_str(elem: panflute.Inline) -> str:
    op: list[str] = []
    for i in elem.walk(noop):
        if isinstance(i, panflute.Str):
            op.append(i.text)
    return " ".join(op)


def get_header_id(h: panflute.Header) -> str:
    return TOMD_RS("-".join(HTI_RF(elem_str(h).lower().strip())).replace(" ", "-"))


def pf_set_element() -> Callable[..., None]:
    def inner(
        d: list[panflute.Element],
        lvl: int,
        elem: panflute.Element,
        og_lvl: Optional[int] = None,
    ) -> None:
        global ld
        if og_lvl is None:
            og_lvl = lvl
        if lvl == 0:
            d.append(elem)
            ld = og_lvl
        elif og_lvl != -1:
            e = d[-1]
            if not isinstance(d[-1], list):
                d[-1] = [DEF_STR, e, []]
            inner(d[-1][-1], lvl - 1, elem, og_lvl)

    return inner


def pfelem2md(elem: panflute.Element, doc: panflute.Element) -> str:
    return pypandoc.convert_text(  # type: ignore[no-any-return]
        json.dumps(
            {
                "pandoc-api-version": doc.to_json()["pandoc-api-version"],
                "meta": {},
                "blocks": [elem.to_json()],
            },
        ),
        to="md",
        format="json",
    )


def rules_fn(rules: dict[Any, Any]) -> dict[str, list[str]]:
    return dd({"": rules.get("del", [])}, rules["repl"])


def sh_inner(
    toc_ls: list[str],
    res_ls: list[list[str]],
    elem: panflute.Header,
    iid: str,
) -> None:
    op = []
    for i in elem.content.walk(noop):
        if isinstance(i, panflute.Str):
            op.append(i.text)

    level = elem.level
    t = " ".join(op)
    a = AW.format(id=iid, content=t)
    toc_ls.append(f'{"    " * (level - 2)}- {a}')
    elem.identifier = ""
    res_ls.append(
        [
            pfelem2md(elem, elem.doc),
            HW.format(n=level, id=iid, title=HA_DEF_STYLE.format(a)),
        ],
    )


def style_header(
    toc_ls: list[str],
    res_ls: list[list[str]],
) -> Callable[..., None]:
    _si = partial(sh_inner, toc_ls, res_ls)

    def inner(
        item: panflute.Element | list[panflute.Element],
        parent: Optional[str] = None,
    ) -> None:
        id_ls = []
        if parent is not None:
            id_ls = [parent]
        if not isinstance(item, list):
            _si(item, "-".join([*id_ls, get_header_id(item.content)]))
        else:
            if len(item) >= 1:
                k = item.pop(0)
                if k == DEF_STR:
                    k, v = item
                    id_ls += [get_header_id(k.content)]
                    iid = "-".join(id_ls)
                    _si(k, iid)
                    for i in v:
                        inner(i, iid)
                else:
                    for i in [k, *item]:
                        inner(i, "-".join(id_ls) if id_ls else None)

    return inner


def style_header_init(
    hls: list[panflute.Element],
    se: Callable[..., None],
) -> Callable[..., None]:
    def inner(elem: panflute.Element, doc: panflute.Doc) -> None:
        if isinstance(elem, panflute.Header):
            se(hls, elem.level - 2, elem)

    return inner


def title_wrap(text: str) -> str:
    ls = []
    overflow = ""
    for i in TITLE_WRAP.wrap(text):
        i, *ofls = TITLE_WRAP.wrap(overflow + i)
        *ils, of = i.split(".")

        if ils:
            i = ".".join(ils) + "."
        else:
            i = of
            of = ""

        ls.append(i)

        overflow = of + "".join(ofls)

    return "\n".join(ls) + overflow


def yield_text(mod: pdoc.Module) -> Generator[Any, None, None]:
    yield mod.name, mod.text()
    sm = {}
    for submod in mod.submodules():
        sm[submod.name] = pdoc_dir(submod.name, rel=True)
        yield from yield_text(submod)

    if not sm:
        return

    header_ls: list[str] = []
    idx_path = pdoc_dir(mod.name)

    m, *ls = mod.name.split(".")
    for idx, i in enumerate(ls[::-1]):
        header_ls.append(LINK.format(text=i, link=f'{"../" * idx}{i}.md'))
    header = ".".join(
        [LINK.format(text=m, link=("../" * (len(ls) - 1)) + "README.md")]
        + header_ls[::-1],
    )

    if sum := mod.supermodule:
        pdoc_dir(sum.name)
        sum = SUPMOD_HEADER_TPL.format(sum.name)
    else:
        sum = ""

    smls = []
    for k, v in sm.items():
        smls.append(f"- [{k}]({v})")

    idx_page = H1_MD.format(
        header=header,
        title=".".join([m, *ls]),
        md=sum + SUBMOD_HEADER_TPL.format("\n".join(smls)),
    )

    with open(idx_path, "w") as f:
        f.write(idx_page)


def ymd2md(
    rules_md: dict[str, dict[str, list[str]]],
    vars_global: dict[str, str],
    vars_local: dict[str, dict[str, str]],
    rip: Path,
) -> None:
    fm = {}
    hls: list[panflute.Element] = []
    toc_ls: list[str] = []
    res_ls: list[list[str]] = []
    tp = False

    out = os.path.join(
        DOCS_OP,
        os.path.relpath(os.path.join(*rip.parts[:-1]), DOCS_INPUT).lstrip("./"),
        f"{rip.stem}.md",
    )

    print(f"Generating {out}")

    rf = frontmatter.load(rip)
    md = repl(rf.content, rules_fn(rules_md))
    md_data: str = pypandoc.convert_text(md, "json", format="md")
    d = dict(  # type: ignore[call-overload]
        vars_global,
        **vars_local.get(rip.stem, {}),
    )

    if title := rf.get("title"):
        fm["title"] = title
        if link := rf.get("link"):
            md = H1_LINK_MD_STH.format(header=title, link=link, md=md)
        else:
            md = H1_MD_STH.format(header=title, md=md)

    for k, v in d.items():
        md = md.replace("{{" + k + "}}", str(v))

    panflute.run_filter(
        style_header_init(hls, pf_set_element()),
        doc=panflute.load(StringIO(md_data)),
    )
    style_header(toc_ls, res_ls)(hls)

    for k, v in res_ls:
        if not tp:
            toc_html = pypandoc.convert_text("\n".join(toc_ls), "html", format="md")
            toc_html = toc_html.replace(">\n<", "><").strip().replace("\n", " ")
            v = '\n<div class="toc">' + TOC_H2 + toc_html + "</div>\n\n" + v
            tp = True
        md = md.replace(k, v, 1)

    if VAR_RE.search(md):
        for row_num, line in enumerate(md.splitlines(), start=1):
            print(f'WARNING File "{out}", line {row_num}:')
            for match in VAR_RE.finditer(line):
                print(f'    unused variable "{match.group()}"')

    with open(inmd(out), "w") as f:
        f.write(md)


def src_docs_individual(module_name: str, module_docs: str) -> None:
    module_fn = pdoc_dir(module_name)

    if os.path.exists(module_fn):
        with open(module_fn, "a") as f:
            f.write("\n" + module_docs)
    else:
        print(f"Generating {module_fn}")
        with open(module_fn, "w") as f:
            f.write(
                version_module_title_header_md(
                    os.path.join(
                        DOCS_IP_DOCS_VER,
                        *[str(i) for i in VLS[0:2]],
                        "api",
                        pdoc_dir(module_name, rel=True),
                    ),
                    module_docs,
                ),
            )


def src_docs() -> None:
    run_mp_star(src_docs_individual, yield_text(PROJECT))


def mako2md_inner(input_path: str) -> None:
    pip = Path(input_path)
    stem = "README" if pip.stem == "index" else pip.stem
    op = os.path.join(DOCS_OP, *pip.parts[2:-1], f"{stem}.md")
    mytemplate = Template(filename=input_path)
    tpl_rd = mytemplate.render(cwd=dn(input_path))
    with open(op, "w") as f:
        f.write(tpl_rd)


def mako_glob_inner_inner(glob: str) -> list[str]:
    return [str(i) for i in Path(".").rglob(glob)]


def mako_glob_inner() -> list[list[str]]:
    return run_mp(mako_glob_inner_inner, MAKO_GEN["glob"])  # type: ignore[no-any-return]


def mako2md() -> None:
    # Initialize Variables
    makos = []

    for glob_res_ls in mako_glob_inner():
        makos += glob_res_ls

    for i in MAKO_GEN["path"]:
        input_path = os.path.join(DOCS_INPUT, i)
        if os.path.isfile(input_path):
            makos.append(input_path)
        else:
            print(f"WARNING: not found: {input_path}")

    run_mp(mako2md_inner, makos)


def version_module_title_header_md(module: Path | str, md: str) -> str:
    """
    Given a Path object or string path relative to `wh_dev.yml:docs/input`.

    Args:
        path (`str`): Path to traverse.
        sep (`str`): Seperator of the path for individual indexes.

    Returns:
        tuple[int, dict[str, int]]: _description_
    """
    if isinstance(module, str):
        module = Path(module)
    elif not isinstance(module, Path):
        raise Exception(
            f"`module` expected to be of type `pathlib.Path` or `str`, but is instead of type `{type(module)}`.",
        )

    header_ls: list[str] = []
    ls = [*module.relative_to(DIDV_PATH).parts[3:-1], module.stem]
    for idx, j in enumerate(ls[::-1]):
        header_ls.append(LINK.format(text=j, link=f'{"../" * idx}{j}.md'))
    header = ".".join(
        [
            LINK.format(text=PNH, link=("../" * (len(ls) - 1)) + "README.md"),
            *header_ls[::-1],
        ],
    )

    return H1_MD.format(title=".".join([PNH, *ls]), header=header, md=md)


def ver_docs() -> str:
    ndd = {}
    u_ls = sorted(listdir(DOCS_IP_DOCS_VER), reverse=True)

    for i in DIDV_PATH.rglob("*.ymd"):
        out = inmd(
            os.path.join(
                DOCS_OP,
                os.path.relpath(os.path.join(*i.parts[:-1]), DOCS_INPUT).lstrip("./"),
                f"{i.stem}.md",
            ),
        )
        print(f"Generating {out}")
        with open(out, "w") as f:
            f.write(version_module_title_header_md(i, i.read_text()))

    with open(os.path.join(DOCS_OP_DOCS_VER, "README.md"), "w") as f:
        f.write(
            H1_STH.format(header="All Versions")
            + "\n".join(f"- [Version {u}.x.x.x]({u}/README.md)" for u in u_ls),
        )
    for u in u_ls:
        d_ls = sorted(listdir(os.path.join(DOCS_IP_DOCS_VER, u)), reverse=True)
        with open(
            os.path.join(DOCS_OP_DOCS_VER, u, "README.md"),
            "w",
        ) as f:
            f.write(
                H1_STH.format(header=f"Version {u}.x.x.x")
                + "\n".join(f"- [Version {u}.{d}.x.x]({d}/README.md)" for d in d_ls),
            )

        for d in d_ls:
            index_mmd = os.path.join(DOCS_IP_DOCS_VER, u, d, "index.mmd")
            md_op = "[Documentation](api/README.md)"
            if os.path.exists(index_mmd):
                with open(index_mmd) as f:
                    md_op = f.read() + "\n\n" + md_op

            with open(os.path.join(DOCS_OP_DOCS_VER, u, d, "README.md"), "w") as f:
                f.write(H1_STH.format(header=f"Version {u}.{d}.x.x") + md_op)

            ndd[f"{u}.{d}"] = os.path.join(
                os.path.relpath(DOCS_OP_DOCS_VER, DOCS_OP).lstrip("./"),
                u,
                d,
                "README.md",
            )

    lk = list(ndd.keys())[-1]
    ndd[f"{lk} (Current)"] = ndd.pop(lk)

    nd = yaml.dump(dict(reversed(ndd.items())), default_flow_style=False)
    return "\n".join([f"    - {i}" for i in nd.strip().split("\n")][::-1])


def mkdocs_build(
    vars_global: "CustomDict",
    rules_site: dict[str, dict[str, list[str]]],
    nd: str,
) -> None:
    info_yml = {}

    for k, (str_fmt, kls) in INFO_TPLS.items():
        vd = {i: GLOBAL_VARS.dir(i, "None") for i in kls}
        if str_fmt is None:
            op = " ".join([str(i) for i in vd.values()])
        else:
            op = str_fmt.format(*vd.values(), **vd)
        info_yml[k] = op

    # Modify `mkdocs.yml`
    mkdocs_mod("info", info_yml)
    mkdocs_mod("dir", MKDOCS_MOD_DOCS)
    mkdocs_mod("nav docs", nd)

    with open("mkdocs.yml", "w") as f:
        f.write(MKDOCS_YML)
    shutil.copy("mkdocs.yml", "mkdocs.bak.yml")

    for dirpath, _, filenames in os.walk(DOCS_OP):
        for filename in filenames:
            input_path = os.path.join(dirpath, filename)
            with open(input_path) as f:
                contents = f.read()
                contents = repl(contents, rules_fn(rules_site))
                # Modify the contents of the file here

            # Create output directory if it doesn't exist
            output_subdir = os.path.join(DOCS_OP_TMP, os.path.relpath(dirpath, DOCS_OP))
            os.makedirs(output_subdir, exist_ok=True)

            output_path = os.path.join(output_subdir, filename)
            with open(output_path, "w") as f:
                f.write(contents)

    run_cmd("mkdocs build")


def main() -> None:
    # Derived Constants
    rules = MD_RULES_VARS["rules"]
    vars = MD_RULES_VARS["vars"]

    rules_md = rules["md"]
    rules_site = rules["site"]
    vars_global = vars["global"]
    vars_local = vars["local"]

    if os.path.isdir(DOCS_OP):
        shutil.rmtree(DOCS_OP)
    ymd2md_fn = partial(ymd2md, rules_md, vars_global, vars_local)

    dip = Path(DOCS_INPUT)
    raw_md_ls = [str(i) for i in dip.rglob("*.ymd")]
    for ignore in DOCS["ignore"]:
        raw_md_ls = [
            i for i in raw_md_ls if i not in [str(j) for j in dip.rglob(ignore)]
        ]

    run_mp(ymd2md_fn, [Path(i) for i in raw_md_ls])
    nd = ver_docs()
    src_docs()
    mako2md()

    for i in Path(DOCS_OP).rglob("*.md"):
        title = i.stem
        istr = str(i)
        with open(istr) as f:
            post = frontmatter.load(f)

        if title := post.get("title"):
            op_title = title_wrap(title)
            post["title"] = op_title

        with open(istr, "w") as f:
            f.write(frontmatter.dumps(post))

    if os.path.isdir(".cache/plugin"):
        shutil.rmtree(".cache/plugin")

    if os.path.isdir(DOCS_OP_TMP):
        shutil.rmtree(DOCS_OP_TMP)
    shutil.copytree(
        os.path.join(DOCS_INPUT, "assets"),
        os.path.join(DOCS_OP_TMP, "assets"),
    )
    mkdocs_build(vars_global, rules_site, nd)
    shutil.copytree(os.path.join(DOCS_INPUT, "assets"), os.path.join(DOCS_OP, "assets"))
