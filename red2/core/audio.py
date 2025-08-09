# -*- coding: utf-8 -*-
import time, uuid, queue
from pathlib import Path
import numpy as np
import sounddevice as sd
import soundfile as sf

TMP = Path.cwd() / "tmp_audio"
TMP.mkdir(exist_ok=True)

class Recorder:
    def __init__(self, samplerate=16000, channels=1, dtype="int16"):
        self.samplerate = samplerate
        self.channels = channels
        self.dtype = dtype
        self._q = queue.Queue()
        self._stream = None
        self._frames = []
        self._level = 0.0
        self._level_decay = 0.2  # smoothing factor (0..1)
        self._t0 = None
        self.last_duration = 0.0

    def _callback(self, indata, frames, time_info, status):
        if status:
            pass
        self._q.put(indata.copy())
        # compute RMS level (0..1)
        try:
            x = indata.astype(np.float32)
            if x.ndim > 1:
                x = x.mean(axis=1, keepdims=True)
            rms = float(np.sqrt(np.mean(np.square(x))) / 32768.0)
            self._level = (1.0 - self._level_decay) * self._level + self._level_decay * min(1.0, rms * 4.0)
        except Exception:
            pass

    def current_level(self) -> float:
        return float(max(0.0, min(1.0, self._level)))

    def start(self):
        self._frames = []
        self._level = 0.0
        self._t0 = time.time()
        self.last_duration = 0.0
        self._stream = sd.InputStream(samplerate=self.samplerate, channels=self.channels, dtype=self.dtype, callback=self._callback)
        self._stream.start()

    def stop(self) -> str:
        if self._stream is None:
            return ""
        self._stream.stop()
        self._stream.close()
        self._stream = None
        # drain queue
        while not self._q.empty():
            self._frames.append(self._q.get())
        if not self._frames:
            self.last_duration = 0.0
            return ""
        data = np.concatenate(self._frames, axis=0)
        # compute duration
        self.last_duration = float(len(data) / float(self.samplerate))
        fname = TMP / f"rec_{int(time.time())}_{uuid.uuid4().hex[:6]}.wav"
        sf.write(str(fname), data, self.samplerate, subtype="PCM_16")
        return str(fname)
