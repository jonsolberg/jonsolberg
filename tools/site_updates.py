#!/usr/bin/env python3
# Builds site/updates.json for jonsolberg.se: the latest version of each app, and one "update" entry
# per app and day – the highest version released that day, with the changes of all that day's
# versions merged – plus "history", every version ever published with its number and changes, for the
# full list of changes on jonsolberg.se/changes.html. The website reads the file straight from GitHub (its own server can't reach the
# GitHub API). Run by .github/workflows/site-data.yml every hour.
# Copyright (C) 2026 Jon Solberg - GPL v3 or later, see LICENSE.
import json, os, re, sys, urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

USER = 'jonsolberg'
TZ = ZoneInfo('Europe/Stockholm')
APPS = {
    'plektrum': 'Plektrum', 'strymoniridiumcontrol': 'Iridium Control', 'wamplerterraformcontrol': 'Terraform Control',
    'rc500editor': 'RC-500 Editor', 'hxstompcontrol': 'HX Stomp Control', 'midi_muppet_max': 'MIDI Muppet Max',
    'tactus': 'Tactus', 'levain': 'Levain', 'tea-timer': 'Tea Timer', 'wallpaper': 'Wallpapers',
    'efx-le-loop-swither-editor': 'EFX-LE Editor',
}
DAYS_PER_APP = 6
SKIP = re.compile(r'^(Merge|Update project overview|Cache-bust|Screenshot|README|Release workflow|Rename|Docs?:|Bump)', re.I)


def api(path):
    req = urllib.request.Request('https://api.github.com/' + path, headers={
        'Accept': 'application/vnd.github+json', 'User-Agent': 'jonsolberg-site-data',
        **({'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN']} if os.environ.get('GITHUB_TOKEN') else {})})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def version(tag):
    parts = re.findall(r'(android|linux|windows)-([\d.]+)', tag, re.I)
    if len(parts) > 1:
        return ' · '.join(f'{k.capitalize()} {v}' for k, v in parts)
    return re.sub(r'^v\.?', '', tag, flags=re.I)


def vkey(v):
    return [int(x) for x in re.findall(r'\d+', v)]


def local_day(iso):
    return datetime.fromisoformat(iso.replace('Z', '+00:00')).astimezone(TZ).date().isoformat()


def changes(repo, day):
    start = datetime.fromisoformat(day).replace(tzinfo=TZ)
    return changes_between(repo, start, start + timedelta(days=1))


def changes_between(repo, start, end, limit=160):
    utc = lambda d: d.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    commits = api(f'repos/{USER}/{repo}/commits?per_page=100&until={utc(end)}'
                  + (f'&since={utc(start)}' if start else ''))
    out = []
    for c in reversed(commits):
        msg = c['commit']['message'].split('\n', 1)[0].strip()
        if not msg or SKIP.match(msg) or msg.startswith('APK from'):
            continue
        msg = re.sub(r'^v?[\d.]+(\s*\([^)]*\))?\s*:\s*', '', msg)
        msg = re.sub(r'^(Android \S+, Linux \S+, Windows \S+|[\w -]+ \d[\d.]*)\s*:\s*', '', msg)
        for part in re.split(r';\s*|,\s*(?=install note|README)', msg, flags=re.I):
            part = part.strip().rstrip('.')
            if not part or re.search(r'README|install note in|GitHub Pages\)?$', part, re.I):
                continue
            part = part[0].upper() + part[1:]
            if part not in out:
                out.append(part)
    text = '; '.join(out)
    return text if len(text) <= limit else text[:limit - 3].rstrip() + '…'


def main():
    path = 'site/updates.json'
    old = open(path).read() if os.path.exists(path) else ''
    try:
        known = {(h['repo'], h['version']): h for h in json.loads(old).get('history', [])}
    except Exception:
        known = {}
    versions, updates, history = {}, [], []
    for repo, name in APPS.items():
        try:
            rels = [r for r in api(f'repos/{USER}/{repo}/releases?per_page=50') if not r['draft'] and not r['prerelease']]
        except Exception as e:                       # one missing repo must not stop the rest
            print(f'{repo}: {e}', file=sys.stderr)
            continue
        if not rels:
            continue
        rels.sort(key=lambda r: r['published_at'], reverse=True)
        versions[repo] = {'version': version(rels[0]['tag_name']), 'date': local_day(rels[0]['published_at'])}
        by_day = {}
        for r in rels:
            d, v = local_day(r['published_at']), version(r['tag_name'])
            best = by_day.get(d)
            if best is None or vkey(v) > vkey(best['v']):
                by_day[d] = {'v': v}
        for d in sorted(by_day, reverse=True)[:DAYS_PER_APP]:
            u = {'date': d, 'repo': repo, 'title': f"{name} {by_day[d]['v']}", 'text': changes(repo, d),
                 'url': f'https://github.com/{USER}/{repo}/releases', 'kind': 'update'}
            updates.append(u)
            # the full list keeps every version ever seen (the releases are replaced, so the file is the record)
            known[(repo, by_day[d]['v'])] = {'date': d, 'repo': repo, 'app': name, 'version': by_day[d]['v'],
                                             'text': u['text'], 'url': u['url']}
    updates.sort(key=lambda u: u['date'], reverse=True)
    history = sorted(known.values(), key=lambda h: (h['date'], h['app']), reverse=True)
    data = {'versions': versions, 'updates': updates, 'history': history}
    os.makedirs('site', exist_ok=True)
    new = json.dumps(data, ensure_ascii=False, indent=1) + '\n'
    if new != old:
        open(path, 'w').write(new)
        print('site/updates.json updated')
    else:
        print('no change')


if __name__ == '__main__':
    main()
