#!/usr/bin/env python3
"""Convert cached Classic small_city to Fortress and rasterize collision geometry."""
import argparse
import copy
import json
import math
import re
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
try:
    import collada
except ImportError:
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'artifacts/python'))
    import collada
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]


def pose(text):
    x,y,z,r,p,yaw=map(float,(text or '0 0 0 0 0 0').split())
    cr,sr,cp,sp,cy,sy=math.cos(r),math.sin(r),math.cos(p),math.sin(p),math.cos(yaw),math.sin(yaw)
    result=np.eye(4)
    result[:3,:3]=[[cy*cp,cy*sp*sr-sy*cr,cy*sp*cr+sy*sr],[sy*cp,sy*sp*sr+cy*cr,sy*sp*cr-cy*sr],[-sp,cp*sr,cp*cr]]
    result[:3,3]=[x,y,z]
    return result


def hull(points):
    points=sorted(set((round(float(x),4),round(float(y),4)) for x,y in points))
    if len(points)<3:return []
    def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    lower=[]
    for p in points:
        while len(lower)>1 and cross(lower[-2],lower[-1],p)<=0:lower.pop()
        lower.append(p)
    upper=[]
    for p in reversed(points):
        while len(upper)>1 and cross(upper[-2],upper[-1],p)<=0:upper.pop()
        upper.append(p)
    return lower[:-1]+upper[:-1]


def clipped_xy(triangles,low=.15,high=2.5):
    triangles=triangles[(triangles[:,:,2].min(axis=1)<=high)&(triangles[:,:,2].max(axis=1)>=low)]
    if not len(triangles):return []
    inside=triangles[(triangles[:,:,2]>=low)&(triangles[:,:,2]<=high)]
    points=[inside[:,:2]]
    for a,b in ((0,1),(1,2),(2,0)):
        start,end=triangles[:,a,:],triangles[:,b,:]
        for level in (low,high):
            valid=((start[:,2]<level)&(end[:,2]>level))|((start[:,2]>level)&(end[:,2]<level))
            if valid.any():
                s,e=start[valid],end[valid]
                t=(level-s[:,2])/(e[:,2]-s[:,2])
                points.append((s+t[:,None]*(e-s))[:,:2])
    return hull(np.vstack(points))


def mesh_triangles(path):
    if path.suffix.lower()=='.dae':
        mesh=collada.Collada(str(path),ignore=[collada.common.DaeUnsupportedError])
        triangles=[]
        for geometry in mesh.scene.objects('geometry'):
            for primitive in geometry.primitives():
                if hasattr(primitive,'triangleset'):primitive=primitive.triangleset()
                if hasattr(primitive,'vertex_index'):
                    indices=np.asarray(primitive.vertex_index)
                    if indices.ndim==2 and indices.shape[1]==3:
                        triangles.append(np.asarray(primitive.vertex)[indices])
        data=np.concatenate(triangles)*float(mesh.assetInfo.unitmeter or 1)
        if mesh.assetInfo.upaxis=='Y_UP':data=data[:,:,[0,2,1]]*np.array([1,-1,1])
        elif mesh.assetInfo.upaxis=='X_UP':data=data[:,:,[2,1,0]]*np.array([-1,1,1])
        return data
    if path.suffix.lower()=='.obj':
        vertices=[];faces=[]
        for line in path.read_text(errors='replace').splitlines():
            fields=line.split()
            if fields and fields[0]=='v':vertices.append(list(map(float,fields[1:4])))
            elif fields and fields[0]=='f':
                idx=[int(x.split('/')[0]) for x in fields[1:]]
                idx=[x-1 if x>0 else len(vertices)+x for x in idx]
                faces.extend((idx[0],idx[i],idx[i+1]) for i in range(1,len(idx)-1))
        return np.asarray(vertices)[np.asarray(faces)]
    raise ValueError(f'Unsupported collision mesh: {path}')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--cache',type=Path,default=ROOT/'assets/small_city')
    args=parser.parse_args()
    cache=args.cache.resolve()
    models=cache/'models'
    original=cache/'worlds/small_city.original.world'
    tree=ET.parse(original)
    world=tree.getroot().find('world')
    world.set('name','small_city')
    for tag in ('gui','physics','state'):
        for item in list(world.findall(tag)):world.remove(item)
    physics=ET.SubElement(world,'physics',name='agile_physics',type='ignored')
    ET.SubElement(physics,'max_step_size').text='0.001'
    ET.SubElement(physics,'real_time_factor').text='1.0'
    for name in ('Physics','UserCommands','SceneBroadcaster','Sensors','Imu','NavSat'):
        filename={'UserCommands':'user-commands','SceneBroadcaster':'scene-broadcaster','NavSat':'navsat'}.get(name,name.lower())
        plugin=ET.SubElement(world,'plugin',filename=f'libignition-gazebo-{filename}-system.so',name=f'ignition::gazebo::systems::{name}')
        if name=='Sensors':ET.SubElement(plugin,'render_engine').text='ogre2'
    sky=world.find('scene/sky')
    if sky is not None:world.find('scene').remove(sky)
    for light in world.findall('light'):
        shadows=light.find('cast_shadows')
        if shadows is not None:shadows.text='false'
    generated=cache/'generated';generated.mkdir(exist_ok=True)
    Image.new('RGB',(4,4),(128,128,255)).save(generated/'flat_normal.png')
    # Canonical image paths avoid Classic global material-path assumptions.
    for model_dir in models.iterdir():
        if not model_dir.is_dir():continue
        images={p.name:p for p in model_dir.rglob('*') if p.is_file() and p.suffix.lower() in ('.png','.jpg','.jpeg','.dds')}
        for path in model_dir.rglob('*.dae'):
            document=ET.parse(path)
            root_tag=document.getroot().tag
            if root_tag.startswith('{'):
                ET.register_namespace('',root_tag[1:].split('}')[0])
            changed=False
            for image in document.getroot().iter():
                if image.tag.endswith('}image'):
                    for item in image:
                        if item.tag.endswith('}init_from') and item.text:
                            name=Path(item.text.replace('file://','')).name
                            if name in images:
                                item.text='file:///opt/agile_assets/'+images[name].relative_to(cache).as_posix()
                                changed=True
            if changed:document.write(path,encoding='utf-8',xml_declaration=True)
        for path in model_dir.rglob('*.mtl'):
            lines=[]
            for line in path.read_text(errors='replace').splitlines():
                parts=line.split()
                if parts and parts[0].startswith('map_') and parts[-1] in images:
                    parts[-1]='/opt/agile_assets/'+images[parts[-1]].relative_to(cache).as_posix()
                    line=' '.join(parts)
                lines.append(line)
            path.write_text('\n'.join(lines)+'\n',encoding='utf-8')

    # Runtime copies are adapted; original Git checkouts remain unchanged.
    for path in models.rglob('*.sdf'):
        root=ET.parse(path).getroot()
        for element in root.iter():
            if element.tag in ('normal','uri') and element.text and 'file://media/materials/textures/flat_normal.png' in element.text:
                element.text='file:///opt/agile_assets/generated/flat_normal.png'
        for material in root.findall('.//material'):
            script=material.find('script')
            if script is not None:
                material.remove(script)
                if material.find('diffuse') is None:ET.SubElement(material,'diffuse').text='0.55 0.6 0.65 1'
        ET.indent(root)
        ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)
    roads=[]
    for road in list(world.findall('road')):
        points=[list(map(float,p.text.split())) for p in road.findall('point')]
        width=float(road.findtext('width'))
        for index,(a,b) in enumerate(zip(points,points[1:])):
            length=math.hypot(b[0]-a[0],b[1]-a[1]);yaw=math.atan2(b[1]-a[1],b[0]-a[0])
            roads.append({'a':a[:2],'b':b[:2],'width':width})
            model=ET.SubElement(world,'model',name=f"{road.get('name')}_surface_{index}")
            ET.SubElement(model,'static').text='true'
            ET.SubElement(model,'pose').text=f'{(a[0]+b[0])/2} {(a[1]+b[1])/2} {a[2]} 0 0 {yaw}'
            link=ET.SubElement(model,'link',name='road')
            visual=ET.SubElement(link,'visual',name='asphalt')
            ET.SubElement(ET.SubElement(ET.SubElement(visual,'geometry'),'box'),'size').text=f'{length} {width} .01'
            ET.SubElement(ET.SubElement(visual,'material'),'diffuse').text='.15 .15 .17 1'
        world.remove(road)
    polygons=[];mesh_cache={}
    def resolve(uri):
        if uri.startswith('model://'):return models/uri[len('model://'):]
        raise ValueError(f'Unresolved collision URI: {uri}')
    def inspect_model(model,parent,label):
        transform=parent@pose(model.findtext('pose'))
        for link in model.findall('link'):
            link_tf=transform@pose(link.findtext('pose'))
            for collision in link.findall('collision'):
                tf=link_tf@pose(collision.findtext('pose'));geo=collision.find('geometry')
                if geo is None or geo.find('plane') is not None:continue
                points=None;triangles=None
                if geo.find('mesh') is not None:
                    mesh=geo.find('mesh');path=resolve(mesh.findtext('uri'))
                    if path not in mesh_cache:mesh_cache[path]=mesh_triangles(path)
                    data=mesh_cache[path]*list(map(float,mesh.findtext('scale','1 1 1').split()))
                    triangles=data@tf[:3,:3].T+tf[:3,3]
                elif geo.find('box') is not None:
                    size=np.array(list(map(float,geo.findtext('box/size').split())))
                    points=np.array([[i,j,k] for i in (-.5,.5) for j in (-.5,.5) for k in (-.5,.5)])*size
                elif geo.find('cylinder') is not None or geo.find('sphere') is not None:
                    item=geo.find('cylinder') if geo.find('cylinder') is not None else geo.find('sphere')
                    radius=float(item.findtext('radius'));height=float(item.findtext('length',str(2*radius)))
                    points=np.array([[radius*math.cos(a),radius*math.sin(a),z] for a in np.linspace(0,2*math.pi,24,endpoint=False) for z in (-height/2,height/2)])
                elif geo.find('polyline') is not None:continue
                else:raise ValueError(f'Unsupported geometry in {label}: {[x.tag for x in geo]}')
                if triangles is not None:polygon=clipped_xy(triangles)
                elif points is not None:
                    points=points@tf[:3,:3].T+tf[:3,3]
                    polygon=hull(points[:,:2]) if points[:,2].min()<=2.5 and points[:,2].max()>=.15 else []
                else:polygon=[]
                if polygon:polygons.append({'name':label+'/'+collision.get('name','collision'),'polygon':polygon})
        for inc in model.findall('include'):
            uri=inc.findtext('uri').strip()
            nested=ET.parse(resolve(uri)/'model.sdf').getroot().find('model')
            inspect_model(nested,transform@pose(inc.findtext('pose')),label+'/'+inc.findtext('name',nested.get('name')))
    for inc in world.findall('include'):
        uri=inc.findtext('uri').strip()
        model=ET.parse(resolve(uri)/'model.sdf').getroot().find('model')
        inspect_model(model,pose(inc.findtext('pose')),inc.findtext('name',model.get('name')))
    for model in world.findall('model'):inspect_model(model,np.eye(4),model.get('name'))
    # Replace Classic built-in material references with explicit SDF colors.
    for material in world.findall('.//material'):
        script=material.find('script')
        if script is not None:
            material.remove(script)
            if material.find('diffuse') is None:ET.SubElement(material,'diffuse').text='.65 .65 .65 1'
    ET.indent(tree)
    tree.write(cache/'worlds/small_city.sdf',encoding='utf-8',xml_declaration=True)
    xmin,ymin,xmax,ymax=-55.,-60.,130.,60.;resolution=.2
    width,height=round((xmax-xmin)/resolution),round((ymax-ymin)/resolution)
    X,Y=np.meshgrid(xmin+(np.arange(width)+.5)*resolution,ymax-(np.arange(height)+.5)*resolution)
    free=np.zeros(X.shape,dtype=bool)
    for road in roads:
        a,b=np.array(road['a']),np.array(road['b']);d=b-a;l=np.linalg.norm(d);u=d/l
        along=(X-a[0])*u[0]+(Y-a[1])*u[1]
        across=-(X-a[0])*u[1]+(Y-a[1])*u[0]
        free|=(along>=-road['width']/2)&(along<=l+road['width']/2)&(abs(across)<=road['width']/2)
    image=np.where(free,254,0).astype(np.uint8)
    for obstacle in polygons:
        polygon=obstacle['polygon'];mask=np.ones(X.shape,dtype=bool)
        for a,b in zip(polygon,polygon[1:]+polygon[:1]):
            mask&=(b[0]-a[0])*(Y-a[1])-(b[1]-a[1])*(X-a[0])>=0
        image[mask]=0
    maps=cache/'maps';maps.mkdir(exist_ok=True)
    (maps/'small_city.pgm').write_bytes(f'P5\n{width} {height}\n255\n'.encode()+image.tobytes())
    (maps/'small_city.yaml').write_text(f'image: small_city.pgm\nmode: trinary\nresolution: {resolution}\norigin: [{xmin},{ymin},0.0]\nnegate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.25\n')
    scene={'name':'small_city','bounds':[xmin,ymin,xmax,ymax],'resolution':resolution,'roads':roads,'obstacles':polygons,'map_policy':'Known road corridors intersected with z-sliced conservative collision hulls; off-road is occupied.'}
    (maps/'small_city_scene.json').write_text(json.dumps(scene,indent=2)+'\n',encoding='utf-8')
    print(f'Converted {len(world.findall("include"))} includes, {len(roads)} road segments, {len(polygons)} collision footprints.')


if __name__=='__main__':main()

