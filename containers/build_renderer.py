#!/usr/bin/env python3
"""Build a hash-pinned Ubuntu Ogre renderer with the NV-copy compatibility patch."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import urllib.request

metadata = json.loads(Path('/source/ogre_next.json').read_text())
work = Path('/build')
work.mkdir(exist_ok=True)
for name, expected in metadata['files'].items():
    data = urllib.request.urlopen(metadata['source_base']+name, timeout=120).read()
    if hashlib.sha256(data).hexdigest() != expected:
        raise RuntimeError('Source checksum mismatch: '+name)
    (work/name).write_bytes(data)
subprocess.run(['dpkg-source','--no-check','-x',str(work/'ogre-next_2.2.5+dfsg3-0ubuntu2.dsc'),str(work/'ogre')],check=True)
subprocess.run(['patch','-p1','--input=/source/'+metadata['patch']],cwd=work/'ogre',check=True)
options = ['-DCMAKE_BUILD_TYPE=RelWithDebInfo','-DOGRE_BUILD_DOCS=OFF','-DOGRE_BUILD_SAMPLES=OFF','-DOGRE_INSTALL_SAMPLES=OFF','-DOGRE_INSTALL_SAMPLES_SOURCE=OFF','-DOGRE_BUILD_COMPONENT_HLMS=ON','-DOGRE_BUILD_COMPONENT_HLMS_PBS=ON','-DOGRE_BUILD_COMPONENT_HLMS_UNLIT=ON','-DOGRE_BUILD_COMPONENT_OVERLAY=ON','-DOGRE_BUILD_COMPONENT_PLANAR_REFLECTIONS=ON','-DOGRE_BUILD_RENDERSYSTEM_GLES2=OFF','-DOGRE_CONFIG_UNIX_NO_X11=OFF','-DOGRE_CONFIG_THREADS=0','-DOGRE_CONFIG_THREAD_PROVIDER=std','-DOGRE_FULL_RPATH=OFF','-DOGRE_GLSUPPORT_USE_EGL_HEADLESS=ON','-DOGRE_GLSUPPORT_USE_GLX=ON','-DOGRE_SIMD_NEON=ON','-DOGRE_SIMD_SSE2=ON','-DOGRE_LIB_DIRECTORY=/usr/lib/x86_64-linux-gnu']
subprocess.run(['cmake','-S',str(work/'ogre'),'-B',str(work/'out'),*options],check=True)
def definitions(path):
    return sorted(line.strip() for line in path.read_text().splitlines() if line.startswith('#define OGRE_'))
if definitions(work/'out/include/OgreBuildSettings.h') != definitions(Path('/usr/include/OGRE-Next/OgreBuildSettings.h')):
    generated=set(definitions(work/'out/include/OgreBuildSettings.h'))
    installed=set(definitions(Path('/usr/include/OGRE-Next/OgreBuildSettings.h')))
    raise RuntimeError('Ogre ABI definitions differ: generated-only='+repr(sorted(generated-installed))+' installed-only='+repr(sorted(installed-generated)))
subprocess.run(['cmake','--build',str(work/'out'),'--target','RenderSystem_GL3Plus','--parallel','6'],check=True)
plugins = list((work/'out').rglob('RenderSystem_GL3Plus.so'))
if len(plugins) != 1:
    raise RuntimeError('Expected one matching renderer plugin')
output = Path('/renderer');output.mkdir()
shutil.copy2(plugins[0],output/'RenderSystem_GL3Plus.so')
subprocess.run(['strip','--strip-unneeded',str(output/'RenderSystem_GL3Plus.so')],check=True)
shutil.copy2(work/'ogre/debian/copyright',output/'copyright')
metadata['plugin_sha256'] = hashlib.sha256((output/'RenderSystem_GL3Plus.so').read_bytes()).hexdigest()
metadata['patch_sha256'] = hashlib.sha256(Path('/source/'+metadata['patch']).read_bytes()).hexdigest()
(output/'provenance.json').write_text(json.dumps(metadata,indent=2)+'\n')
