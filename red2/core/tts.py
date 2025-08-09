
from __future__ import annotations
import os, threading, tempfile, asyncio, ctypes
from typing import Optional, Callable

def _mci_play_mp3_blocking(path: str) -> None:
    mci = ctypes.windll.winmm.mciSendStringW
    alias = "redtts"
    try:
        mci(f'open "{path}" type mpegvideo alias {alias}', None, 0, 0)
        mci(f'play {alias} wait', None, 0, 0)
    finally:
        try:
            mci(f'close {alias}', None, 0, 0)
        except Exception:
            pass

def _edge_rate(rate: int) -> str:
    pct = int(max(-25, min(25, (int(rate) - 175) * 0.5)))
    return f"{'+' if pct >= 0 else ''}{pct}%"

def _edge_vol(vol: float) -> str:
    pct = int(max(-10, min(10, (float(vol) - 0.9) * 50)))
    return f"{'+' if pct >= 0 else ''}{pct}%"

class _EdgeTTS:
    def __init__(self, rate: int = 175, volume: float = 0.9, voice: Optional[str] = None):
        self.rate = int(rate)
        self.volume = float(volume)
        self.voice = voice or "ru-RU-SvetlanaNeural"
        self._th = None
        self._stop = False

    def set_voice(self, voice_id: str) -> None:
        if voice_id:
            self.voice = voice_id

    def speak(self, text: str, on_done: Optional[Callable] = None) -> None:
        self.stop()
        self._stop = False
        self._th = threading.Thread(target=self._run, args=(text, on_done), daemon=True)
        self._th.start()

    def stop(self) -> None:
        self._stop = True

    def _run(self, text: str, on_done: Optional[Callable]) -> None:
        try:
            import edge_tts
        except Exception as e:
            print("Edge TTS not available:", e)
            if on_done: on_done()
            return
        fd, path = tempfile.mkstemp(prefix="red_edge_tts_", suffix=".mp3")
        os.close(fd)

        async def _synth():
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=_edge_rate(self.rate),
                volume=_edge_vol(self.volume),
            )
            await communicate.save(path)

        try:
            asyncio.run(_synth())
            if self._stop:
                if on_done: on_done()
                return
            _mci_play_mp3_blocking(path)
        except Exception as e:
            print("Edge TTS error:", e)
        finally:
            try: os.remove(path)
            except Exception: pass
            if on_done: on_done()

class _SysTTS:
    def __init__(self, rate: int = 175, volume: float = 0.9, voice: Optional[str] = None):
        try:
            import pyttsx3
        except Exception as e:
            raise RuntimeError("pyttsx3 is required for system TTS") from e
        self.eng = pyttsx3.init()
        try: self.eng.setProperty("rate", int(rate))
        except Exception: pass
        try: self.eng.setProperty("volume", float(volume))
        except Exception: pass
        if voice: self.set_voice(voice)

    def set_voice(self, voice_id: str) -> None:
        if not voice_id: return
        try:
            for v in self.eng.getProperty("voices") or []:
                vid = getattr(v, "id", "")
                if vid == voice_id:
                    self.eng.setProperty("voice", vid); break
        except Exception: pass

    def speak(self, text: str, on_done: Optional[Callable] = None) -> None:
        def _run():
            try:
                self.eng.say(text)
                self.eng.runAndWait()
            finally:
                if on_done: on_done()
        threading.Thread(target=_run, daemon=True).start()

    def stop(self) -> None:
        try: self.eng.stop()
        except Exception: pass

def _load_prefs() -> dict:
    try:
        from ..ui import user_prefs
        return user_prefs.load()
    except Exception:
        return {}

class TTS:
    """
    Автоматически подхватывает смену движка/голоса/скорости:
    перед каждым .speak() перечитывает prefs и, если что‑то поменялось,
    пересоздаёт внутренний движок.
    """
    def __init__(self, rate: int = 175, volume: float = 0.9, voice: Optional[str] = None):
        self._impl = None
        self._cur = {
            "engine": None, "rate": None, "volume": None, "voice": None
        }
        self._ensure_impl(force=True, defaults={"rate": rate, "volume": volume, "voice": voice})

    def _ensure_impl(self, force: bool = False, defaults: dict | None = None) -> None:
        prefs = _load_prefs()
        engine = (prefs.get("tts_engine") or "edge").lower()
        rate   = int(prefs.get("tts_rate", (defaults or {}).get("rate", 175)))
        volume = float(prefs.get("tts_volume", (defaults or {}).get("volume", 0.9)))
        voice  = prefs.get("tts_voice", (defaults or {}).get("voice"))

        changed = force or any([
            self._cur["engine"] != engine,
            self._cur["rate"]   != rate,
            self._cur["volume"] != volume,
            self._cur["voice"]  != voice,
        ])
        if not changed:
            return

        if engine == "system":
            try:
                self._impl = _SysTTS(rate=rate, volume=volume, voice=voice)
            except Exception as e:
                print("System TTS failed, fallback to Edge:", e)
                self._impl = _EdgeTTS(rate=rate, volume=volume, voice=voice or "ru-RU-SvetlanaNeural")
        else:
            self._impl = _EdgeTTS(rate=rate, volume=volume, voice=voice or "ru-RU-SvetlanaNeural")

        self._cur.update({"engine": engine, "rate": rate, "volume": volume, "voice": voice})

    def set_voice(self, voice_id: str) -> None:
        try:
            self._impl.set_voice(voice_id)
        except Exception:
            pass

    def speak(self, text: str, on_done: Optional[Callable] = None) -> None:
        self._ensure_impl()
        self._impl.speak(text, on_done=on_done)

    def stop(self) -> None:
        try: self._impl.stop()
        except Exception: pass
