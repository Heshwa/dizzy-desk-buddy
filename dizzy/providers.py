"""Interchangeable providers with bounded calls, safe fallback and latency traces."""
import asyncio
import json
import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo
import aiohttp
from .tools import SYSTEM, TOOLS


class GeminiProvider:
    def __init__(self):
        self.model = os.getenv('DIZZY_GEMINI_MODEL', 'gemini-3.1-flash-lite')
        self.fallback_model = os.getenv('DIZZY_GEMINI_FALLBACK_MODEL', 'gemini-3.5-flash-lite')
        self.histories = {}
        self.last_trace = {}
        self.primary_retry_at = 0
        self.client = None
        self.client_key = None

    async def close(self):
        if self.client is not None:
            await self.client.aio.aclose()
            self.client = None

    async def get_client(self):
        from google import genai
        from google.genai import types
        key = os.getenv('GEMINI_API_KEY')
        if not key:
            raise RuntimeError('Gemini needs GEMINI_API_KEY in the local .env file. Local device commands still work.')
        if self.client is None or self.client_key != key:
            await self.close()
            self.client = genai.Client(api_key=key, http_options=types.HttpOptions(
                timeout=10000, retry_options=types.HttpRetryOptions(attempts=1)))
            self.client_key = key
        return self.client

    def remember(self, device, text, answer):
        from google.genai import types
        turn = [types.Content(role='user', parts=[types.Part.from_text(text=text)]),
                types.Content(role='model', parts=[types.Part.from_text(text=answer)])]
        # Completed turns keep conversational text, not old tool/thinking payloads.
        self.histories[device] = (self.histories.get(device, []) + [turn])[-8:]

    @staticmethod
    def transient(exc):
        return (getattr(exc,'code',None) in (408,500,502,503,504)
                or isinstance(exc, (asyncio.TimeoutError,))
                or 'timeout' in type(exc).__name__.lower())

    def config(self, model):
        from google.genai import types
        thinking = types.ThinkingConfig(thinking_budget=0) if '2.5' in model else types.ThinkingConfig(thinking_level='minimal')
        return types.GenerateContentConfig(
            system_instruction=SYSTEM+'\nCurrent time '+datetime.now(ZoneInfo('Asia/Kolkata')).isoformat(),
            tools=[types.Tool(function_declarations=[types.FunctionDeclaration(**t) for t in TOOLS])],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            max_output_tokens=512, thinking_config=thinking)

    async def generate(self, client, model, history, trace):
        started=time.monotonic()
        call={'model':model}
        try:
            response=await asyncio.wait_for(client.aio.models.generate_content(
                model=model,contents=history,config=self.config(model)),11)
            call['ok']=True
            return response
        except Exception as exc:
            detail=str(exc)
            key=os.getenv('GEMINI_API_KEY','')
            if key:detail=detail.replace(key,'[key]')
            call.update(ok=False,code=getattr(exc,'code',None),error_type=type(exc).__name__,detail=detail[:240])
            raise
        finally:
            call['ms']=round((time.monotonic()-started)*1000)
            trace['calls'].append(call)

    async def reply(self, device, text, execute):
        from google.genai import types
        trace={'calls':[],'completed_tools':[]}
        self.last_trace[device]=trace
        client=await self.get_client()
        history=[message for turn in self.histories.get(device,[]) for message in turn]
        history.append(types.Content(role='user',parts=[types.Part.from_text(text=text)]))
        model=self.model
        if self.fallback_model and time.monotonic()<self.primary_retry_at:
            model=self.fallback_model
        try:
            for step in range(6):
                try:
                    response=await self.generate(client,model,history,trace)
                except Exception as exc:
                    # Switch only before executing tools: never replay a partially executed turn.
                    if step==0 and model==self.model and self.fallback_model and self.fallback_model!=model and self.transient(exc):
                        self.primary_retry_at=time.monotonic()+60
                        model=self.fallback_model
                        response=await self.generate(client,model,history,trace)
                    else:
                        raise
                if not response.candidates or not response.candidates[0].content:
                    raise RuntimeError('Gemini returned no reply. Please try again.')
                history.append(response.candidates[0].content)
                if not response.function_calls:
                    answer=response.text or 'Please try again.'
                    self.remember(device,text,answer)
                    trace['model']=model
                    return answer
                parts=[]
                for call in response.function_calls:
                    result=await execute(call.name,dict(call.args or {}))
                    if result.get('ok'):trace['completed_tools'].append(call.name)
                    parts.append(types.Part.from_function_response(name=call.name,response=result))
                history.append(types.Content(role='user',parts=parts))
            raise RuntimeError('This request needs too many steps. Please use a shorter command.')
        except Exception as exc:
            code=getattr(exc,'code',None)
            if code==429:
                message='Gemini quota or request limit reached. Please try again later.'
            elif code in (401,403):
                message='Gemini rejected access to this project or API key. Check the AI Studio project.'
            elif code in (500,502,503):
                message='Gemini is unavailable right now. Local head, hand and music commands still work.'
            elif code==400:
                message='Gemini rejected the request configuration. Local head, hand and music commands still work.'
            elif code in (408,504) or 'timeout' in type(exc).__name__.lower() or isinstance(exc,asyncio.TimeoutError):
                message='The AI reply timed out. Local head, hand and music commands still work.'
            else:
                message=str(exc) or 'Gemini request failed. Please try again.'
            if trace['completed_tools']:
                message+=' Completed tools: '+', '.join(trace['completed_tools'])+'.'
            key=os.getenv('GEMINI_API_KEY','')
            if key:message=message.replace(key,'[key]')
            raise RuntimeError(message[:400]) from None


class OllamaProvider:
    async def reply(self, device, text, execute):
        messages = [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': text}]
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as session:
            for _ in range(6):
                async with session.post(os.getenv('DIZZY_OLLAMA_URL', 'http://127.0.0.1:11434') + '/api/chat', json={
                    'model': os.getenv('DIZZY_OLLAMA_MODEL', 'qwen3:4b'),
                    'messages': messages, 'tools': [{'type': 'function', 'function': t} for t in TOOLS], 'stream': False,
                }) as response:
                    response.raise_for_status()
                    message = (await response.json())['message']
                messages.append(message)
                if not message.get('tool_calls'):
                    return message['content']
                for call in message['tool_calls']:
                    fn = call['function']
                    result = await execute(fn['name'], fn.get('arguments', {}))
                    messages.append({'role': 'tool', 'tool_name': fn['name'], 'content': json.dumps(result)})
        raise RuntimeError('Too many tool steps')
