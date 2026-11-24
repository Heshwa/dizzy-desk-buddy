"""Build a standalone FreeCAD review document from the connected fit study."""
import json
from pathlib import Path

import FreeCAD as App
import Mesh
import Part

CAD = Path(__file__).resolve().parents[1]
OUT = CAD / 'fit-study'
study = json.loads((OUT / 'connected-fit.json').read_text())
doc = App.openDocument(str(CAD / 'output' / 'Dizzy.FCStd'))
groups = {}
for name,label in [('Installed','Installed component geometry'),
                   ('Plugs','Connector and plug gauges'),
                   ('Harness','Service cable routes')]:
    group = doc.addObject('App::DocumentObjectGroup','Fit_'+name)
    group.Label = label
    groups[name] = group

source_shape = Part.read(str(OUT / 'vendor' / 'adafruit-5807.step'))
source_shape.translate(App.Vector(*study['pd_transform_mm']))
pd = doc.addObject('Part::Feature','Fit_Adafruit_5807')
pd.Shape = source_shape
pd.Label = 'Adafruit HUSB238 5807 · manufacturer STEP'
groups['Installed'].addObject(pd)
for entry in study['meshes']:
    kind = entry['kind']
    if entry['owner']=='usb_c_pd_board' and kind=='body':
        continue
    obj = doc.addObject('Mesh::Feature',entry['id'])
    obj.Mesh = Mesh.Mesh(str((CAD / entry['path']).with_suffix('.stl')))
    obj.Label = entry['owner'].replace('_',' ') + ' · ' + kind
    obj.addProperty('App::PropertyBool','InterferenceFlag','Connected fit')
    obj.InterferenceFlag = entry['flagged']
    if obj.ViewObject:
        obj.ViewObject.ShapeColor = tuple(entry['color'])
    groups['Harness' if kind=='wire' else 'Plugs' if kind in ('gauge','connector') else 'Installed'].addObject(obj)
doc.recompute()
doc.saveAs(str(OUT / 'Dizzy-connected-fit.FCStd'))
print('Saved',len(groups['Installed'].Group),'component meshes/solids and',
      len(groups['Harness'].Group),'service routes.',flush=True)
