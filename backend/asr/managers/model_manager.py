# backend/asr/managers/model_manager.py

import uuid
import gc
from backend.asr.schemas import ModelRegister
from backend.db.asr_db import (
    save_model_to_db,
    update_model_loaded_status,
    update_model_status,
    get_models_from_db
)
from backend.asr.managers.openvino_engine import OpenVINOASREngine

class ModelManager:
    def __init__(self):
        self.models = {}
        self._initialize_models()

    def _initialize_models(self):
        models = get_models_from_db()
        for m in models:
            model_id = m['id']
            self.models[model_id] = {
                "info": ModelRegister(**m),
                "instance": None,
                "loaded": False,
                "latency": None
            }
            if m.get("loaded", False):
                try:
                    self.load_model(model_id)
                except Exception as e:
                    print(f"[ERROR] 자동 로드 실패: {e}")

    def register(self, info):
        model_id = str(uuid.uuid4())
        self.models[model_id] = {
            "info": info,
            "instance": None,
            "loaded": False,
            "latency": None
        }
        save_model_to_db(model_id, info)
        return model_id

    def load_model(self, model_id):
        model = self.models.get(model_id)
        if not model:
            raise ValueError(f"모델 ID {model_id} 정보 없음")

        info = model["info"]
        fw = info.framework.lower()

        try:
            if fw == "openvino":
                engine = OpenVINOASREngine()
                engine.load(info.path, info.device)
                model["instance"] = engine
            elif fw == "azure":
                model["instance"] = None
                print(f"[INFO] Azure 모델 '{info.name}'은 로컬 로드 생략")
            else:
                raise ValueError(f"지원하지 않는 프레임워크입니다: {fw}")

            model["loaded"] = True
            model["latency"] = None
            update_model_loaded_status(model_id, True, None)
            update_model_status(model_id, "active")

        except Exception as e:
            model["loaded"] = False
            model["latency"] = None
            print(f"[ERROR] 모델 로드 실패: {e}")

    def unload_model(self, model_id):
        model = self.models.get(model_id)
        if not model or not model['loaded']:
            print(f"[INFO] 모델 {model_id}은 로드되어 있지 않거나 존재하지 않습니다.")
            return False

        try:
            info = model['info']
            fw = info.framework.lower()

            if fw == 'openvino':
                engine = model['instance']
                if engine:
                    engine.unload()
                    gc.collect()

            elif fw == 'azure':
                print(f"[INFO] Azure 모델 '{info.name}'은 언로드 대상이 아닙니다.")

            model["instance"] = None
            model["loaded"] = False
            model["latency"] = None
            update_model_loaded_status(model_id, False, None)
            update_model_status(model_id, "idle")
            print(f"[INFO] 모델 {info.name} 언로드 완료")
            return True

        except Exception as e:
            print(f'[ERROR] 모델 언로드 실패: {e}')
            return False

    def infer(self, model_id, audio, language):
        model = self.models.get(model_id)
        if not model or not model["loaded"]:
            raise ValueError("모델이 로드되지 않았습니다.")
        return model["instance"].infer(audio, language)

    def get_status(self):
        return [
            {
                "id": k,
                "name": v["info"].name,
                "main": v["info"].main,
                "language": v["info"].language,
                "framework": v["info"].framework,
                "device": v["info"].device,
                "loaded": v["loaded"],
                "latency": v["latency"],
                "logo": v["info"].logo,
                "status": self._get_status(v)
            }
            for k, v in self.models.items()
        ]

    def _get_status(self, model):
        if not model["loaded"]:
            return "loading"

        fw = model["info"].framework.lower()
        if model["latency"] is None:
            if fw == "azure":
                return "idle"
            return "error"

        return "idle"

model_manager = ModelManager()