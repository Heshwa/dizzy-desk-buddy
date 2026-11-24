"""Keep self-contained Wokwi chips and firmware pins aligned to their sources."""
from pathlib import Path
import json
root=Path(__file__).resolve().parent
header=(root/'wokwi/dizzy_devices.h').read_text()
for name,kind,addr in [('ds3231',1,104),('pca9685',2,64),('husb238',3,8)]:
 (root/'wokwi'/f'{name}.chip.c').write_text(f'// Generated from dizzy_devices.h; self-contained for Wokwi compilation.\n#define CHIP_KIND {kind}\n#define CHIP_ADDRESS {addr}\n'+header)
pins=json.loads((root.parent/'hardware/pinmap.json').read_text())['pins']
(root/'wokwi/pins.h').write_text('#pragma once\n// Generated from hardware/pinmap.json.\n'+''.join(f'constexpr int {name.upper()} = {item["gpio"]};\n' for name,item in pins.items()))
