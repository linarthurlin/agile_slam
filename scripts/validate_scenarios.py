#!/usr/bin/env python3
"""Reject destinations whose configured vehicle footprint leaves free map cells."""
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def validate_routes(config, routes):
    if not routes:return
    from PIL import Image
    metadata={}
    for line in (ROOT/'assets/small_city/maps/small_city.yaml').read_text().splitlines():
        if ':' in line:
            key,value=line.split(':',1);metadata[key.strip()]=value.strip()
    resolution=float(metadata['resolution']);ox,oy,_=json.loads(metadata['origin'])
    vehicle=json.loads((ROOT/'ros2_ws/src/gem_description/config/vehicle.json').read_text())
    image=Image.open(ROOT/'assets/small_city/maps'/metadata['image']).convert('L')
    front=vehicle['body_front_x']-vehicle['rear_axle_x']
    rear=vehicle['body_rear_x']-vehicle['rear_axle_x']
    half=vehicle['body_half_width'];padding=resolution/math.sqrt(2)
    for route in routes:
        goals=list(config['routes'][route])
        if route in config.get('starts',{}):
            sx,sy,syaw=config['starts'][route]
            goals.append({'name':'known_start','x':sx+vehicle['rear_axle_x']*math.cos(syaw),'y':sy+vehicle['rear_axle_x']*math.sin(syaw),'yaw':syaw})
        for goal in goals:
            x,y,yaw=goal['x'],goal['y'],goal['yaw']
            if not all(math.isfinite(v) for v in (x,y,yaw)):raise ValueError('Nonfinite goal: '+goal['name'])
            c,s=math.cos(yaw),math.sin(yaw)
            corners=[(x+c*px-s*py,y+s*px+c*py) for px,py in ((rear,-half),(front,-half),(front,half),(rear,half))]
            imin=math.floor((min(p[0] for p in corners)-ox)/resolution)-1
            imax=math.ceil((max(p[0] for p in corners)-ox)/resolution)+1
            jmin=math.floor((min(p[1] for p in corners)-oy)/resolution)-1
            jmax=math.ceil((max(p[1] for p in corners)-oy)/resolution)+1
            for i in range(imin,imax+1):
                for j in range(jmin,jmax+1):
                    dx=ox+(i+.5)*resolution-x;dy=oy+(j+.5)*resolution-y
                    local_x=c*dx+s*dy;local_y=-s*dx+c*dy
                    if rear-padding<=local_x<=front+padding and abs(local_y)<=half+padding:
                        if not (0<=i<image.width and 0<=j<image.height) or image.getpixel((i,image.height-1-j))<250:
                            raise ValueError(f'Goal footprint intersects occupied/unknown/outside map cells: {route}/{goal["name"]} at ({x}, {y}, {yaw})')
    image.close()


if __name__=='__main__':
    config=json.loads((ROOT/'config/scenarios/small_city.json').read_text(encoding='utf-8-sig'))
    validate_routes(config,list(config['routes']))
    print('Scenario destination footprints are inside free map cells; path feasibility requires live planning.')
