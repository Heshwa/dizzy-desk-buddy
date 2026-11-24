"""Pack local fit meshes into one resource for the browser viewer."""
from base64 import b64encode
import json
from pathlib import Path
CAD=Path(__file__).resolve().parents[1]
fit=CAD/'fit-study'
models=json.loads((fit/'connected-fit.json').read_text())['meshes']
covers=[p for p in json.loads((CAD/'preview-data.json').read_text())['parts']
        if not p['hardware'] and p['region']!='coupon']
path=fit/'fit-view-meshes.json'
path.write_text(json.dumps({m['id']:b64encode((CAD/m['path']).read_bytes()).decode('ascii')
                            for m in models+covers},separators=(',',':')))
print(f'Packed {len(models+covers)} fit meshes in {path.stat().st_size/1e6:.1f} MB')
