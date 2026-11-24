"""Apply the final mechanical details to the saved candidate without re-lofting the palms."""
import csv
import json
import build as b
from helmet import helmet_parts

b.doc=b.App.openDocument(str(b.OUT/'Dizzy.FCStd'))
state=json.loads((b.REPORT/'checks.json').read_text())
b.S=state['scale']
b.results['scale_search']=state['scale_search']
rows={row['part']:row for row in csv.DictReader((b.REPORT/'parts.csv').open())}
for name in ('Printable','Hardware','Calibration'):
    group=b.doc.getObject(name)
    b.groups[name]=group
    for obj in group.Group:
        row=rows.get(obj.Name,{})
        info=dict(id=obj.Name,region=obj.Region,color=b.IVORY,material=obj.Material,shape=obj.Shape,obj=obj,printable=obj.PrintThisPart)
        (b.printed if obj.PrintThisPart else b.hardware).append(info)
        b.shapes[obj.Name]=obj.Shape
b.component_shapes={entry['id'][3:]:entry['shape'] for entry in b.hardware}
for name, shape in helmet_parts(b).items():
    shape=shape.removeSplitter()
    assert shape.isValid() and len(shape.Solids)==1, name
    b.doc.getObject(name).Shape=shape
    b.shapes[name]=shape
    for entry in b.printed:
        if entry['id']==name:
            entry['shape']=shape
            break
# Update the flat sensor allowances beneath the curved pads.
for side, sign in [('left',-1), ('right',1)]:
    item=next(c for c in b.MAN['components'] if c['id']=='crown_'+side)
    center=b.actual_center(item,b.S)
    shape=b.box(item['size_mm'],center)
    item['reference_center_mm'][2]=center[2]/b.S-157
    b.doc.getObject('HW_crown_'+side).Shape=shape
    b.component_shapes['crown_'+side]=shape
b.validation_and_export()
