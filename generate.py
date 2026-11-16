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

    out = []
    out.append(f'<h1 align="center">Hi, I\'m Jon 👋</h1>\n')
    out.append(f'<p align="center">{cfg["intro"]}</p>\n')
    out.append(
        f'<p align="center"><a href="{site}">🌐 jonsolberg.se</a> · '
        f'<a href="{site}/tools.html">🧰 All tools</a> · '
        f'<a href="{site}/games.html">🎮 All games</a> · '
        f'<a href="{cfg["kofi"]}">🍺 Buy me a beer</a>'
        + (f' · <a href="mailto:{cfg["email"]}">✉️ {cfg["email"]}</a>' if cfg.get("email") else "")
        + '</p>\n'
    )

    for sec in sections:
        items = [p for p in projects if p.get("section") == sec["id"]]
        if not items:
            continue
        out.append(f'\n## {sec["title"]}\n')
        if sec.get("note"):
            out.append(f'\n{sec["note"]}\n')
        for p in items:
            r = repos.get(p.get("repo", "").lower()) if p.get("repo") else None
            title = p["name"]
            if r:
                title = f'[{title}]({r["html_url"]})'
            meta = []
            if p.get("platform"):
                meta.append(p["platform"])
            if r and r.get("_release"):
                rel = r["_release"]
                meta.append(f'[{rel["tag_name"]}]({rel["html_url"]})')
            if r:
                meta.append("updated " + ago(r.get("pushed_at"), now))
            line = f'\n**{p.get("emoji", "•")} {title}**'
            if meta:
                line += " · <sub>" + " · ".join(meta) + "</sub>"
            out.append(line + "  \n")
            blurb = p.get("blurb") or (r.get("description") if r else "") or ""
            if blurb:
                out.append(blurb + "  \n")
            links = [f'[{label}]({link(url, site)})' for label, url in p.get("links", [])]
            if r:
                links.append(f'[Source]({r["html_url"]})')
            if links:
                out.append("➜ " + " · ".join(links) + "\n")

    out.append(
        "\n---\n<sub>This page updates itself every day from "
        f"[projects.toml](https://github.com/{USER}/{USER}/blob/main/projects.toml) "
        "and my public repositories. All my code is licensed under GPL v3.</sub>\n"
    )

    text = "".join(out)
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(text)
    print(f"README.md: {len(projects)} projects, {len(repos)} public repos")


if __name__ == "__main__":
    main()
