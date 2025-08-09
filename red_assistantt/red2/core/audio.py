# -*- coding: utf-8 -*-
import os, time, uuid, queue
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

    def _callback(self, indata, frames, time_info, status):
        if status:
            # swallow XRuns but keep recording
            pass
        self._q.put(indata.copy())

    def start(self):
        self._frames = []
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
            return ""
        data = np.concatenate(self._frames, axis=0)
        fname = TMP / f"rec_{int(time.time())}_{uuid.uuid4().hex[:6]}.wav"
        sf.write(str(fname), data, self.samplerate, subtype="PCM_16")
        return str(fname)
