"""Build the user's portable CrossOver bottle; not needed on the target Mac."""
import json
import plistlib
import shutil
from pathlib import Path

root = Path(__file__).resolve().parents[1]
bottle = root / 'bottle-template'
app = root / 'FLAC3D CrossOver Portable.app'
resources = app / 'Contents/Resources'

# Discard only the copied installer's duplicate extraction and old machine links.
duplicate = bottle / 'drive_c/OriginalExtract'
if duplicate.exists():
    shutil.rmtree(duplicate)
for path in (bottle / 'dosdevices').iterdir():
    if path.name != 'c:':
        path.unlink()
for path in (bottle / 'drive_c/users').rglob('*'):
    if path.is_symlink() and str(path.readlink()).startswith('/'):
        path.unlink()
for path in bottle.rglob('.DS_Store'):
    path.unlink()
reg = bottle / 'user.reg'
text = reg.read_text()
text = '\n'.join(line for line in text.split('\n') if not line.startswith('"last project"='))
reg.write_text(text)
for name in ('launch.sh',):
    shutil.copy2(root / 'source' / name, resources / name)
(resources / 'launch.sh').chmod(0o755)
info_path = app / 'Contents/Info.plist'
info = plistlib.loads(info_path.read_bytes())
for key in list(info):
    if key.endswith('UsageDescription'):
        del info[key]
info.update(CFBundleIdentifier='local.flac3d.crossover.portable',
            CFBundleShortVersionString='1.0.0',CFBundleVersion='1',
            NSHighResolutionCapable=True)
info_path.write_bytes(plistlib.dumps(info))
metadata = {'format':1,'source_crossover':'26.3','source_flac3d':'6.00.69',
            'target':'Apple Silicon Mac with installed, activated CrossOver',
            'bottle_name':'FLAC3D-CrossOver-Portable',
            'engine_embedded':False,'project_files_embedded':False,
            'retina':True,'dpi':192,'editor_font':'Arial Unicode MS',
            'user_home_links':'rebound at first launch'}
(resources / 'build-info.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(metadata,ensure_ascii=False))
