"""Inspect exported CAD at rest and at all commanded joint extremes."""
import math
import os
from pathlib import Path
from controller import Supervisor

robot = Supervisor()
head = robot.getFromDef('HEAD').getField('rotation')
left = robot.getFromDef('LEFT').getField('rotation')
right = robot.getFromDef('RIGHT').getField('rotation')
poses = [(0,0,0), (-45,0,120), (45,120,0), (-45,120,120), (45,120,120), (0,0,0)]
test = os.environ.get('DIZZY_CAD_TEST') == '1'
for yaw, l, r in poses:
    head.setSFRotation([0,0,1,math.radians(yaw)])
    left.setSFRotation([-1,0,0,math.radians(l)])
    right.setSFRotation([-1,0,0,math.radians(r)])
    for step in range(2 if test else 28):
        if robot.step(32) == -1:
            raise SystemExit(0)
    for field, angle in ((head,yaw),(left,l),(right,r)):
        assert abs(field.getSFRotation()[3]-math.radians(angle)) < 1e-6
print('CAD_POSES_OK', len(poses), flush=True)
if test:
    result = os.environ.get('DIZZY_CAD_TEST_REPORT')
    if result:
        Path(result).write_text('CAD_POSES_OK '+str(len(poses))+'\n')
    robot.simulationQuit(0)
