"""
Write the files of the docs site that span its versions, in a checkout of the gh-pages branch:

- switcher.json, the versions in the version switcher of the theme
- latest/, a copy of the newest release
- index.html, a redirect to latest/, or to dev/ before the first release
- .nojekyll, so GitHub Pages serves the _static folders

Run it after a build is copied into its folder, dev or x.y.z.
"""

import json
import re
import shutil
import sys
import tomllib
from pathlib import Path

SITE = 'https://djungelorm.github.io/sphinx-csharp'
RELEASE = re.compile(r'\d+\.\d+\.\d+')
ROOT = Path(__file__).resolve().parent.parent


def dev_version() -> str:
    """ The release that main works towards, such as 1.0.0 for 1.0.0rc1 """
    version = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
    return re.match(r'\d+(\.\d+)*', version)[0]


def switcher_entries(releases: list[str], has_dev: bool) -> list[dict]:
    """ The entries of switcher.json, with dev first and the newest release preferred """
    entries = []
    if has_dev:
        entries.append({'name': f'v{dev_version()} (dev)', 'version': 'dev', 'url': f'{SITE}/dev/'})
    for i, release in enumerate(releases):
        entry = {'name': f'v{release}', 'version': release, 'url': f'{SITE}/{release}/'}
        if i == 0:
            entry['name'] += ' (stable)'
            entry['preferred'] = True
        entries.append(entry)
    return entries


def redirect(url: str) -> str:
    return (f'<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            f'<meta http-equiv="refresh" content="0; url={url}">\n<link rel="canonical" href="{url}">\n'
            f'<title>sphinx-csharp documentation</title>\n</head>\n'
            f'<body>Redirecting to the <a href="{url}">sphinx-csharp documentation</a></body>\n</html>\n')


def main() -> int:
    site = Path(sys.argv[1])
    folders = {path.name for path in site.iterdir() if path.is_dir()}
    releases = sorted((name for name in folders if RELEASE.fullmatch(name)),
                      key=lambda name: tuple(map(int, name.split('.'))), reverse=True)
    entries = switcher_entries(releases, 'dev' in folders)
    (site / 'switcher.json').write_text(json.dumps(entries, indent=2) + '\n', encoding='utf-8')

    # Note: GitHub Pages serves static files, so latest/ is a copy of the newest release.
    latest = site / 'latest'
    shutil.rmtree(latest, ignore_errors=True)
    if releases:
        shutil.copytree(site / releases[0], latest)
    (site / 'index.html').write_text(redirect(f'{SITE}/latest/' if releases else f'{SITE}/dev/'), encoding='utf-8')
    (site / '.nojekyll').touch()
    print(f'switcher.json lists {", ".join(entry["version"] for entry in entries)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
