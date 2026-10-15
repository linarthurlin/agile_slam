#!/usr/bin/env python3
"""Fetch the pinned small_city dependency closure into an ignored local cache."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URI = re.compile(r'model://([^/\s<]+)')


def git(*args):
    return subprocess.check_output(['git', *args], text=True, encoding='utf-8').strip()


def checkout(spec, path, patterns):
    if not (path / '.git').exists():
        subprocess.run(['git', 'clone', '--depth', '1', '--filter=blob:none', '--sparse', spec['url'], str(path)], check=True)
    if git('-C', str(path), 'rev-parse', 'HEAD') != spec['commit']:
        subprocess.run(['git', '-C', str(path), 'fetch', '--depth', '1', 'origin', spec['commit']], check=True)
        subprocess.run(['git', '-C', str(path), 'checkout', '--detach', spec['commit']], check=True)
    subprocess.run(['git', '-C', str(path), 'sparse-checkout', 'set', *sorted(patterns)], check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache', type=Path, default=ROOT / 'assets/small_city')
    args = parser.parse_args()
    cache = args.cache.resolve()
    cache.mkdir(parents=True, exist_ok=True)
    sources = json.loads((ROOT / 'config/scenes/small_city_sources.json').read_text(encoding='utf-8-sig'))
    collection = cache / 'sources/collection'
    official = cache / 'sources/gazebo_models'
    checkout(sources['collection'], collection, ['worlds'])
    world = collection / sources['collection']['world']
    pending = set(URI.findall(world.read_text(encoding='utf-8')))
    selected = {}
    cpatterns = {'worlds'}
    gpatterns = set()
    collection_tree = set(git('-C', str(collection), 'ls-tree', '-r', '--name-only', 'HEAD').splitlines())
    # Clone the official metadata once; sparse checkout controls asset downloads.
    checkout(sources['gazebo_models'], official, [])
    official_tree = set(git('-C', str(official), 'ls-tree', '-r', '--name-only', 'HEAD').splitlines())
    while pending:
        names = pending - selected.keys()
        if not names:
            break
        for name in names:
            if f'models/{name}/model.config' in collection_tree:
                selected[name] = 'collection'
                cpatterns.add(f'models/{name}')
            elif f'{name}/model.config' in official_tree:
                selected[name] = 'gazebo_models'
                gpatterns.add(name)
            else:
                raise SystemExit(f'Unresolved model dependency: {name}')
        checkout(sources['collection'], collection, cpatterns)
        checkout(sources['gazebo_models'], official, gpatterns)
        pending = set()
        for name, origin in selected.items():
            directory = collection / 'models' / name if origin == 'collection' else official / name
            for sdf in directory.rglob('*.sdf'):
                pending.update(URI.findall(sdf.read_text(encoding='utf-8', errors='replace')))
        pending -= selected.keys()
    models = cache / 'models'
    models.mkdir(exist_ok=True)
    for name, origin in sorted(selected.items()):
        source = collection / 'models' / name if origin == 'collection' else official / name
        shutil.copytree(source, models / name, dirs_exist_ok=True)
    (cache / 'worlds').mkdir(exist_ok=True)
    shutil.copy2(world, cache / 'worlds/small_city.original.world')
    # Keep upstream notices beside cached assets; do not relicense them as project code.
    for origin, directory in (('collection', collection), ('gazebo_models', official)):
        for path in directory.iterdir():
            if path.is_file() and re.search(r'license|copying|readme', path.name, re.I):
                dest = cache / 'notices' / origin / path.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)
    files = {}
    for path in sorted(models.rglob('*')):
        if path.is_file():
            files[path.relative_to(cache).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {'sources': sources, 'models': selected, 'files': files, 'world_sha256': hashlib.sha256(world.read_bytes()).hexdigest()}
    (cache / 'source_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'Prepared {len(selected)} models, {len(files)} files in {cache}')


if __name__ == '__main__':
    main()
