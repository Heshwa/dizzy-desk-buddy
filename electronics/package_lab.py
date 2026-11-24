"""Package only lab sources/reports and public component documents, never secrets."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
root=Path(__file__).resolve().parent
with ZipFile(root/'dizzy-electronics.zip','w',ZIP_DEFLATED) as archive:
 for file in root.rglob('*'):
  if not file.is_file() or file.name=='dizzy-electronics.zip' or file.suffix=='.dat' or 'toolchain' in file.parts or '__pycache__' in file.parts:continue
  archive.write(file,Path('dizzy-electronics/electronics')/file.relative_to(root))
 for name in ['BOM.csv','SHOPPING_LIST.md','pinmap.json','power.json','ASSEMBLY.md','HANDS_PLAN.md']:
  file=root.parent/'hardware'/name
  if file.exists():archive.write(file,Path('dizzy-electronics/hardware')/name)
 archive.write(root.parent/'Start Electronics Lab.command','dizzy-electronics/Start Electronics Lab.command')
print(root/'dizzy-electronics.zip')
