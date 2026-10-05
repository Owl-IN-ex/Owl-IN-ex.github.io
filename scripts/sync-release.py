"""Build GitHub Pages files with the latest stable ServiceKit release metadata."""
import json
import os
import pathlib
import re
import shutil
import time
import urllib.request

API = 'https://api.github.com/repos/Owl-IN-ex/Owl-IN-ServiceKit/releases/latest'

def fetch_json(url, authenticated=False):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'Owl-IN-release-sync'}
    if authenticated and os.environ.get('GH_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as response:
                return json.load(response)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)

def main():
    release = fetch_json(API, authenticated=True)
    assert not release['draft'] and not release['prerelease']
    version = release['tag_name'].removeprefix('v')
    assert re.fullmatch(r'\d+\.\d+\.\d+', version), 'Unexpected stable release version'
    asset = next(item for item in release['assets'] if item['name'] == f'Owl-IN-ServiceKit-{version}.exe')
    sha256 = (asset.get('digest') or '').removeprefix('sha256:')
    assert re.fullmatch(r'[a-f0-9]{64}', sha256), 'Missing verified SHA-256'
    metadata = {'product': 'Owl-IN ServiceKit', 'version': version, 'tag': release['tag_name'],
                'releaseUrl': release['html_url'], 'downloadUrl': asset['browser_download_url'],
                'sha256': sha256, 'size': asset['size'], 'publishedAt': release['published_at']}
    previous = json.loads(pathlib.Path('release.json').read_text(encoding='utf-8'))
    html = pathlib.Path('index.html').read_text(encoding='utf-8')
    html = html.replace(previous['version'], version).replace(previous['sha256'], sha256)
    html = html.replace(previous['downloadUrl'], metadata['downloadUrl']).replace(previous['releaseUrl'], metadata['releaseUrl'])
    output = pathlib.Path('_site')
    output.mkdir(exist_ok=True)
    (output / 'index.html').write_text(html, encoding='utf-8')
    (output / 'release.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (output / '.nojekyll').touch()
    shutil.copytree('assets', output / 'assets', dirs_exist_ok=True)
    changed = True
    if os.environ.get('GITHUB_EVENT_NAME') == 'schedule':
        try:
            deployed = fetch_json('https://owl-in-ex.github.io/release.json?sync=' + str(int(time.time())))
            changed = deployed != metadata
        except Exception:
            pass
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as stream:
            stream.write(f'changed={str(changed).lower()}\n')
    print(f'Latest stable release: {version}; deployment needed: {changed}')

if __name__ == '__main__':
    main()
