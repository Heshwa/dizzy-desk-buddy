"""Conservative, single-command shortcuts using the same verified action tools."""
import re

IDENTITY = "I'm Dizzy, your pet buddy, created and developed by Heshwa for Yoga."


def route(text):
    text = re.sub(r'[?.!,]+$', '', text.strip().lower()).strip()
    text = re.sub(r'^(?:can|could|would) you\s+', '', text)
    text = re.sub(r'^please\s+|\s+please$', '', text)
    if text in ('who made you', 'who created you', 'who developed you', 'who is your creator', 'who are you'):
        return (None, {}, IDENTITY)
    match = re.fullmatch(r'(?:look|face|(?:turn|rotate|move)(?: your head)?)(?: to)?(?: the)? (left|right|center|centre|straight ahead)', text)
    if match:
        direction = match[1]
        angle = -35 if direction == 'left' else 35 if direction == 'right' else 0
        return ('head_turn', {'degrees': angle}, 'Turning my head ' + ('to the '+direction if angle else 'back to the center') + '.')
    match = re.fullmatch(r'(pause|stop|play|resume)(?: the)? music', text)
    if match:
        command = 'pause' if match[1] in ('pause','stop') else 'play'
        return ('music_control', {'command': command}, 'Music paused.' if command=='pause' else 'Playing music.')
    poses = {'wave your hand':'wave','wave your right hand':'wave','lift your hands':'lift',
             'lift both hands':'lift','raise both hands':'lift','rest your hands':'rest','lower your hands':'rest'}
    if text in poses:
        return ('arms_pose', {'pose':poses[text]}, 'Moving my hands.' if poses[text]!='rest' else 'Lowering my hands.')
    return None
