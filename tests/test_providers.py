from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from google.genai import types
from dizzy.providers import GeminiProvider


class ApiError(Exception):
    def __init__(self,code):self.code=code;super().__init__(str(code))


def response(text='Ready.',call=None):
    parts=[types.Part.from_function_call(name=call,args={'degrees':20})] if call else [types.Part.from_text(text=text)]
    return types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(role='model',parts=parts))])


def provider_with(*answers):
    p=GeminiProvider()
    generate=AsyncMock(side_effect=list(answers))
    client=SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
    p.get_client=AsyncMock(return_value=client)
    return p,generate


@pytest.mark.asyncio
async def test_transient_failure_falls_back_once_then_uses_cooldown():
    p,generate=provider_with(ApiError(503),response('Hello.'),response('Again.'))
    execute=AsyncMock()
    assert await p.reply('a','Hello',execute)=='Hello.'
    assert [call.kwargs['model'] for call in generate.call_args_list]==[p.model,p.fallback_model]
    assert await p.reply('a','Again',execute)=='Again.'
    assert generate.call_args_list[-1].kwargs['model']==p.fallback_model
    execute.assert_not_called()
    assert p.last_trace['a']['calls'][0]['ok']


@pytest.mark.asyncio
async def test_never_switch_models_or_reexecute_actions_after_tool_execution():
    p,generate=provider_with(response(call='head_turn'),ApiError(503))
    execute=AsyncMock(return_value={'ok':True,'result':{'target_degrees':20}})
    with pytest.raises(RuntimeError,match='Completed tools: head_turn'):
        await p.reply('a','Turn the head',execute)
    execute.assert_awaited_once()
    assert len(generate.call_args_list)==2
    assert all(call.kwargs['model']==p.model for call in generate.call_args_list)


@pytest.mark.asyncio
async def test_quota_is_not_reported_as_busy_or_retried_on_other_models():
    p,generate=provider_with(ApiError(429))
    with pytest.raises(RuntimeError,match='quota'):
        await p.reply('a','Hello',AsyncMock())
    assert generate.await_count==1
