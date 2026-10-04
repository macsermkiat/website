"""The projects in content/projects.md (one per ### heading), read at build time so a coaster exists for every
project the writer lists. Plain Python, no bpy.

    projects() -> [{"i": 0, "name": "ProtoCol", "style": "Helles · always on tap", "colourway": "gold"}, ...]
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
PROJECTS_MD = os.path.join(REPO, "content", "projects.md")

# coaster colourways (the printed rim's colour): picked from the project's beer style line, else in turn
COLOURWAYS = ["gold", "brown", "green", "blue", "red"]
SPARE_COLOURWAY = "red"
N_SPARES = 2


def colourway_for(style, i):
    s = (style or "").lower()
    if "helles" in s or "pils" in s or "lager" in s:
        return "gold"
    if "dunkel" in s or "bock" in s or "stout" in s:
        return "brown"
    if "cellar" in s or "keller" in s or "reserve" in s:
        return "green"
    if "weiß" in s or "weiss" in s or "weizen" in s:
        return "blue"
    return COLOURWAYS[i % len(COLOURWAYS)]


def projects(path=PROJECTS_MD):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    # drop front matter
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end > 0:
            text = text[end + 4:]
    out = []
    lines = text.splitlines()
    for k, ln in enumerate(lines):
        m = re.match(r"^###\s+(.+?)\s*$", ln)
        if not m:
            continue
        name = re.sub(r"[*_`]", "", m.group(1)).strip()
        style = ""
        for nxt in lines[k + 1:k + 6]:
            sm = re.match(r"^\s*[*_](.+?)[*_]\s*$", nxt)
            if sm:
                style = sm.group(1).strip()
                break
            if nxt.startswith("#"):
                break
        summary = ""
        for nxt in lines[k + 1:k + 12]:
            if nxt.startswith("#"):
                break
            t = re.sub(r"<!--.*?-->|\[\[.*?\]\]", "", nxt).strip()
            if t and not re.match(r"^[*_].+[*_]$", t):
                summary = t
                break
        i = len(out)
        out.append({"i": i, "name": name, "style": style, "colourway": colourway_for(style, i), "summary": summary})
    return out


def coasters():
    """Every coaster on the Bierstand counter: one per project, then the spares."""
    ps = projects()
    out = [dict(p, project=p["name"]) for p in ps]
    for k in range(N_SPARES):
        out.append({"i": len(out), "name": "A spare Bierdeckel", "style": "", "colourway": SPARE_COLOURWAY,
                    "project": None})
    return out


if __name__ == "__main__":
    for c in coasters():
        print(c)
