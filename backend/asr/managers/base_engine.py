# backend/asr/managers/base_engine.py
class BaseASREngine:
    def load(self, path: str, device: str):
        raise NotImplementedError

    def infer(self, audio_np, language: str):
        raise NotImplementedError

    def unload(self):
        raise NotImplementedError
