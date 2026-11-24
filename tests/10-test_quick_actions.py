import pytest
from dizzy.quick_actions import route, IDENTITY, CREATOR
from dizzy.tools import SYSTEM
from dizzy.server import Hub


@pytest.mark.parametrize('text', ['look right','Can you rotate your head to the right?','please turn your head to the right'])
def test_explicit_head_commands_route_locally(text):
    assert route(text)[:2]==('head_turn',{'degrees':35})


@pytest.mark.parametrize('text', ["don't look right",'look right and pause music','why do you look right','set an alarm for seven','turn right in ten minutes','if I say hello look right'])
def test_negated_conditional_compound_and_scheduled_requests_use_model(text):
    assert route(text) is None


def test_creator_identity_matches_system_message():
    assert route('Who developed you?')==(None,{},IDENTITY)
    assert CREATOR in SYSTEM and CREATOR in IDENTITY


@pytest.mark.asyncio
async def test_local_command_works_when_cloud_is_unavailable_and_confirms_only_success():
    class Cloud:
        async def reply(self,*args):raise AssertionError('Do not contact cloud')
    hub=Hub(Cloud());calls=[]
    async def command(device,action,args=None):
        calls.append((action,args));return {'ok':True,'result':{}}
    hub.command=command
    result=await hub.chat('dizzy-a','Can you rotate your head to the right?',speak=False)
    assert result['ok'] and result['route']=='local'
    assert ('head_turn',{'degrees':35}) in calls
    async def failed(device,action,args=None):
        return {'ok':False,'error':'Phone is disconnected'} if action=='music_control' else {'ok':True,'result':{}}
    hub.command=failed
    result=await hub.chat('dizzy-a','pause music',speak=False)
    assert not result['ok'] and 'disconnected' in result['error'] and 'reply' not in result

