"""Package the CAD files with the reference inputs required to rebuild."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
ROOT=Path(__file__).resolve().parents[2]
CAD=ROOT/'cad'
destination=CAD/'Dizzy-CAD-review.zip'
with ZipFile(destination,'w',ZIP_DEFLATED,compresslevel=5) as archive:
    for path in sorted(CAD.rglob('*')):
        rel=path.relative_to(CAD)
        if (not path.is_file() or path==destination or
            any(part.startswith('.') or part=='__pycache__' for part in rel.parts) or
            path.suffix in ('.FCBak','.pyc','.log') or path.name=='build-error.txt'):
            continue
        archive.write(path, path.relative_to(ROOT))
    for path in sorted((ROOT/'assets').glob('dizzy-*.obj')):
        archive.write(path,path.relative_to(ROOT))
    for name in ['dizzy/design.py','scripts/build_hands.py','hardware/BOM.csv','hardware/ASSEMBLY.md','hardware/pinmap.json','protos/Dizzy.proto','reports/seated-companion.png']:
        archive.write(ROOT/name,name)
print(destination)
