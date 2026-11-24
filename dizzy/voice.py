"""Push-to-talk recording, whisper.cpp transcription, and Piper speech."""
import asyncio
from pathlib import Path
import shutil
import select
import subprocess
import sys
import uuid
import time
import wave

ROOT = Path(__file__).resolve().parents[1]


class Voice:
    def __init__(self):
        self.recording = None
        self.recording_device = None
        self.capture_path = None
        self._piper = None
        self.last_speech_timings = {}

    def start(self, device):
        if self.recording is not None:
            raise RuntimeError('A recording is already in progress')
        folder = ROOT / 'runtime'
        folder.mkdir(exist_ok=True)
        raw_path = folder / f'recording-{uuid.uuid4().hex}.pcm'
        with open(folder / 'microphone.log', 'ab') as errors:
            process = subprocess.Popen(
                [sys.executable, '-m', 'dizzy.capture', str(raw_path)],
                cwd=ROOT, stdout=subprocess.PIPE, stderr=errors,
            )
        try:
            readable, _, _ = select.select([process.stdout], [], [], 8)
            if not readable or process.stdout.readline().strip() != b'READY':
                raise RuntimeError('The microphone could not start. Check macOS microphone access and runtime/microphone.log.')
        except Exception:
            self.end_capture(process)
            raise
        finally:
            process.stdout.close()
        self.recording = process
        self.recording_device = device
        self.capture_path = raw_path
        return process

    @staticmethod
    def end_capture(process):
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1)

    def cancel(self):
        process = self.recording
        self.recording = None
        self.recording_device = None
        if process is not None:
            self.end_capture(process)

    def stop(self, device):
        if self.recording is None or device != self.recording_device:
            raise RuntimeError('No recording is active for this Dizzy')
        raw_path = self.capture_path
        self.cancel()
        audio = raw_path.read_bytes()
        raw_path.unlink(missing_ok=True)
        if not audio:
            raise RuntimeError('No microphone audio was recorded')
        path = raw_path.with_suffix('.wav')
        with wave.open(str(path), 'wb') as wav:
            wav.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
            wav.writeframes(audio[:len(audio) // 2 * 2])
        return path

    async def transcribe(self, path):
        executable = shutil.which('whisper-cli')
        model = ROOT / 'models' / 'ggml-base.en.bin'
        if not executable or not model.exists():
            raise RuntimeError('Install whisper.cpp and download the English base model with scripts/setup.sh')
        output = ROOT / 'runtime' / ('transcript-' + uuid.uuid4().hex)
        process = await asyncio.create_subprocess_exec(executable, '-m', str(model), '-f', str(path), '-l', 'en', '-otxt', '-of', str(output), '-np',
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
        try:
            _, error = await asyncio.wait_for(process.communicate(), 60)
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            raise RuntimeError('Speech transcription timed out. Please record a shorter request.') from None
        except asyncio.CancelledError:
            process.kill()
            await process.communicate()
            raise
        if process.returncode:
            raise RuntimeError('Speech transcription failed: ' + error.decode()[-200:])
        text = output.with_suffix('.txt').read_text().strip()
        if not text:
            raise RuntimeError('No speech detected')
        return text

    async def speak(self, text, volume=0.5):
        model = ROOT / 'models' / 'en_US-lessac-medium.onnx'
        if not model.exists():
            raise RuntimeError('Download the Piper voice with scripts/setup.sh')
        path = ROOT / 'runtime' / ('reply-' + uuid.uuid4().hex + '.wav')
        started=time.monotonic()
        def synthesize():
            from piper import PiperVoice, SynthesisConfig
            if self._piper is None:
                self._piper=PiperVoice.load(str(model))
            with wave.open(str(path),'wb') as output:
                self._piper.synthesize_wav(text,output,syn_config=SynthesisConfig(volume=volume))
        await asyncio.to_thread(synthesize)
        synthesized=time.monotonic()
        self.last_speech_timings={'tts_ms':round((synthesized-started)*1000)}
        player = await asyncio.create_subprocess_exec('afplay', str(path))
        code = await player.wait()
        self.last_speech_timings['playback_ms']=round((time.monotonic()-synthesized)*1000)
        if code:
            raise RuntimeError('Speaker playback failed. Check the Mac sound output device and volume.')
        return str(path)
