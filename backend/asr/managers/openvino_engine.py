# backend/asr/managers/openvino_engine.py
import numpy as np
import openvino_genai
from backend.asr.managers.base_engine import BaseASREngine

class OpenVINOASREngine(BaseASREngine):
    def __init__(self):
        self.pipeline = None

    def load(self, path, device):
        self.pipeline = openvino_genai.WhisperPipeline(path, device=device)

    def infer(self, audio_np, language):
        audio_np = np.array(audio_np, dtype=np.float32)
        result = self.pipeline.generate(audio_np, language=language)
        return result.texts

    def unload(self):
        openvino_genai.openvino.shutdown()
        self.pipeline = None
