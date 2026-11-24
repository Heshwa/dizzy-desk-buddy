import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from v2.app.pet import Pet

with tempfile.TemporaryDirectory() as folder:
    state=Path(folder)/'persist.json'
    time=[1730000000.]
    def boot():return Pet('standalone',state,now=lambda:time[0],motion_now=lambda:time[0])
    before=boot()
    before.execute('favorites_set',{'ids':[1,3,5]})
    before.execute('reaction_assign',{'event':'greeting','ids':[15,23]})
    due=datetime.fromtimestamp(time[0],before.zone)+timedelta(seconds=6)
    before.execute('alarm_set',{'at':due.isoformat(),'label':'Power cycle'})
    duplicate={'id':'greeting-checked','sender':'pair','gesture':'wave','expires':time[0]+10}
    assert before.receive_gesture(duplicate)
    after=boot()
    assert after.settings['favorites']==[1,3,5]
    assert after.settings['reactions']['greeting']==[15,23]
    assert after.receive_gesture(duplicate) and not after.events
    time[0]+=7
    after.tick()
    assert after.ringing['label']=='Power cycle'
    assert not after.receive_gesture({**duplicate,'expires':time[0]-1})
    print('PASS: restart retained favorites, event assignment, and alarm. Duplicate ignored and expired gesture rejected.')
