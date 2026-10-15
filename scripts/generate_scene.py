#!/usr/bin/env python3
"""Generate a small SDF scene and occupancy map from one obstacle inventory."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]

def generate():
    spec = json.loads((ROOT / 'config/scenarios/navigation.json').read_text(encoding='utf-8-sig'))
    sdf = ET.parse(ROOT / 'ros2_ws/src/gem_gazebo/worlds/baseline.sdf').getroot()
    world = sdf.find('world')
    world.set('name', spec['name'])
    for model in list(world.findall('model')):
        if model.get('name') != 'ground':
            world.remove(model)
    xmin, ymin, xmax, ymax = spec['bounds']
    boxes = list(spec['obstacles']) + [
        {'name': 'north', 'center': [(xmin+xmax)/2, ymax], 'size': [xmax-xmin, .3, 2]},
        {'name': 'south', 'center': [(xmin+xmax)/2, ymin], 'size': [xmax-xmin, .3, 2]},
        {'name': 'west', 'center': [xmin, (ymin+ymax)/2], 'size': [.3, ymax-ymin, 2]},
        {'name': 'east', 'center': [xmax, (ymin+ymax)/2], 'size': [.3, ymax-ymin, 2]},
    ]
    for box in boxes:
        model = ET.SubElement(world, 'model', name=box['name'])
        ET.SubElement(model, 'static').text = 'true'
        x, y = box['center']
        sx, sy, sz = box['size']
        ET.SubElement(model, 'pose').text = f'{x} {y} {sz/2} 0 0 0'
        link = ET.SubElement(model, 'link', name='body')
        for kind in ('collision', 'visual'):
            item = ET.SubElement(link, kind, name=kind)
            geometry = ET.SubElement(item, 'geometry')
            ET.SubElement(ET.SubElement(geometry, 'box'), 'size').text = f'{sx} {sy} {sz}'
            if kind == 'visual':
                ET.SubElement(ET.SubElement(item, 'material'), 'ambient').text = '0.7 0.5 0.25 1'
    ET.indent(sdf)
    world_text = ET.tostring(sdf, encoding='unicode') + '\n'
    resolution = spec['resolution']
    width, height = round((xmax-xmin)/resolution), round((ymax-ymin)/resolution)
    pixels = bytearray([254]) * (width*height)
    for row in range(height):
        y = ymax - (row+.5)*resolution
        for col in range(width):
            x = xmin + (col+.5)*resolution
            if any(abs(x-b['center'][0]) <= b['size'][0]/2 and abs(y-b['center'][1]) <= b['size'][1]/2 for b in boxes):
                pixels[row*width+col] = 0
    maps = ROOT / 'ros2_ws/src/agile_navigation/maps'
    return {
        ROOT / 'ros2_ws/src/gem_gazebo/worlds/navigation.sdf': world_text.encode(),
        maps / 'navigation_scene.json': (json.dumps(spec,indent=2)+'\n').encode(),
        maps / 'navigation.pgm': f'P5\n{width} {height}\n255\n'.encode()+pixels,
        maps / 'navigation.yaml': f'image: navigation.pgm\nmode: trinary\nresolution: {resolution}\norigin: [{xmin}, {ymin}, 0.0]\nnegate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.25\n'.encode(),
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for path, data in generate().items():
        if args.check:
            if not path.exists() or path.read_bytes() != data:
                raise SystemExit(f'Scene/map out of date: {path.relative_to(ROOT)}')
        else:
            path.write_bytes(data)
    print('Scene and map are consistent.')

if __name__ == '__main__':
    main()
