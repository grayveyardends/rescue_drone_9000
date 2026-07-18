from faster_whisper import WhisperModel
import sounddevice as sd
import numpy as np

# STT
class STT:
    def __init__(self):
        self.model = WhisperModel("base", device="cuda", 
                                   compute_type="float16")
    def listen(self, duration=5, samplerate=16000):
        audio = sd.rec(int(duration * samplerate), 
                      samplerate=samplerate, channels=1, dtype='float32')
        sd.wait()
        segments, _ = self.model.transcribe(audio.flatten(), 
                                            language=None)  # auto-detect
        return " ".join(s.text for s in segments)

import subprocess

class TTS:
    VOICES = {
        "en": "en_US-lessac-medium",
        "ml": "ml_IN-female-medium"
    }
    def speak(self, text: str, lang: str = "en"):
        voice = self.VOICES.get(lang, self.VOICES["en"])
        subprocess.Popen(
            f'echo "{text}" | piper --model {voice} --output-raw | aplay -r 22050 -f S16_LE -t raw -',
            shell=True
        )
