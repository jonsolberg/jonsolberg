#!/usr/bin/env python3
# Builds README.md (the github.com/jonsolberg profile page) from projects.toml
# plus live data from the GitHub API.
#
# Copyright (C) 2026 Jon Solberg
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version. See LICENSE.

import datetime as dt
import json
import os
import sys
import tomllib
import urllib.error
import urllib.request

USER = "jonsolberg"
API = "https://api.github.com"
SKIP = {USER}  # the profile repo itself


def api(path):
    req = urllib.request.Request(API + path, headers={"Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def ago(iso, now):
    if not iso:
        return ""
    t = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    days = (now - t).days
    if days < 1:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 30:
        return f"{days} days ago"
    months = days // 30
    if months < 12:
        return f"{months} month{'s' if months > 1 else ''} ago"
    years = days // 365
    return f"{years} year{'s' if years > 1 else ''} ago"


def link(url, site):
    return url if url.startswith("http") else site + url


def main():
    with open("projects.toml", "rb") as f:
        cfg = tomllib.load(f)
    site = cfg["site"]
    now = dt.datetime.now(dt.timezone.utc)

    # Live data for all public, non-fork repos
    repos = {}
    try:
        page = 1
        while True:
            batch = api(f"/users/{USER}/repos?per_page=100&type=owner&page={page}") or []
            for r in batch:
                if r["fork"] or r["archived"] or r["private"] or r["name"] in SKIP:
                    continue
                repos[r["name"].lower()] = r
            if len(batch) < 100:
                break
            page += 1
        for name, r in repos.items():
            rel = api(f"/repos/{USER}/{r['name']}/releases/latest")
            r["_release"] = rel
    except Exception as e:  # keep building from the config alone
        print("GitHub API unavailable:", e, file=sys.stderr)

    projects = cfg.get("project", [])
    known = {p["repo"].lower() for p in projects if p.get("repo")}
    for name, r in sorted(repos.items(), key=lambda kv: kv[1]["pushed_at"] or "", reverse=True):
        if name not in known:
            projects.append({
                "repo": r["name"],
                "name": r["name"],
                "section": "new",
                "emoji": "✨",
                "blurb": r.get("description") or "",
                "links": [["Website", r["homepage"]]] if r.get("homepage") else [],
            })

    sections = cfg["section"] + [{"id": "new", "title": "✨ New & other"}]

    def esc(t):
        return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def cell(p):
        r = repos.get(p.get("repo", "").lower()) if p.get("repo") else None
        links = [(label, link(url, site)) for label, url in p.get("links", [])]
        if r:
            main = r["html_url"]
        elif p.get("repo"):
            main = f"https://github.com/{USER}/{p['repo']}"
        else:
            main = links[0][1] if links else site
        meta = []
        if p.get("platform"):
            meta.append(esc(p["platform"]))
        if r and r.get("_release"):
            rel = r["_release"]
            meta.append(f'<a href="{rel["html_url"]}">{esc(rel["tag_name"])}</a>')
        if r:
            links.append(("Source", r["html_url"]))
        tagline = p.get("tagline") or p.get("blurb") or (r.get("description") if r else "") or ""
        h = ['<td width="50%" valign="top">']
        if p.get("image"):
            h.append(f'<a href="{main}"><img src="{p["image"]}" alt="{esc(p["name"])}" width="100%"></a>')
        h.append(f'<h3>{p.get("emoji", "")} <a href="{main}">{esc(p["name"])}</a></h3>')
        if meta:
            h.append("<sub>" + " · ".join(meta) + "</sub><br>")
        if tagline:
            h.append(esc(tagline) + "<br>")
        if links:
            h.append("<sub>" + " · ".join(f'<a href="{u}">{esc(l)}</a>' for l, u in links) + "</sub>")
        h.append("</td>")
        return "\n".join(h)

    out = []
    out.append(f'<p align="center"><a href="{site}"><img src="assets/banner.jpg" alt="Jon Solberg – apps and games" width="100%"></a></p>\n\n')
    links_row = [
        f'<a href="{site}">🌐 Website</a>',
        f'<a href="{site}/tools.html">🧰 Tools</a>',
        f'<a href="{site}/music.html">🎸 Music</a>',
        f'<a href="{site}/games.html">🎮 Games</a>',
        f'<a href="{cfg["kofi"]}">🍺 Buy me a beer</a>',
    ]
    if cfg.get("email"):
        links_row.append(f'<a href="mailto:{cfg["email"]}">✉️ {cfg["email"]}</a>')
    out.append('<p align="center">' + " &nbsp;·&nbsp; ".join(links_row) + "</p>\n\n")
    out.append(f'<p align="center"><i>{esc(cfg["intro"])}</i></p>\n')

    for sec in sections:
        items = [p for p in projects if p.get("section") == sec["id"]]
        if not items:
            continue
        out.append(f'\n<h2 align="center">{sec["title"]}</h2>\n')
        if sec.get("note"):
            out.append(f'<p align="center"><sub>{esc(sec["note"])}</sub></p>\n')
        out.append("\n<table>\n")
        for i in range(0, len(items), 2):
            pair = items[i:i + 2]
            out.append("<tr>\n" + "\n".join(cell(p) for p in pair))
            if len(pair) == 1:
                out.append('\n<td width="50%"></td>')
            out.append("\n</tr>\n")
        out.append("</table>\n")

    out.append(
        '\n<p align="center"><sub>This page updates itself every day from '
        f'<a href="https://github.com/{USER}/{USER}/blob/main/projects.toml">projects.toml</a> '
        "and my public repositories · All my code is licensed under GPL v3</sub></p>\n"
    )

    text = "".join(out)
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(text)
    print(f"README.md: {len(projects)} projects, {len(repos)} public repos")


if __name__ == "__main__":
    main()
