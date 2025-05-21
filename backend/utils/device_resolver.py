import comtypes
from pycaw.pycaw import AudioUtilities, IMMDeviceEnumerator, EDataFlow, DEVICE_STATE
from pycaw.constants import CLSID_MMDeviceEnumerator

def resolve_input_device_id(friendly_name: str) -> str | None:
    """
    시스템에서 입력 장치를 조회한 뒤 지정된 FriendlyName과 일치하는 장치의 ID를 반환
    """
    deviceEnumerator = comtypes.CoCreateInstance(
        CLSID_MMDeviceEnumerator,
        IMMDeviceEnumerator,
        comtypes.CLSCTX_INPROC_SERVER
    )

    collection = deviceEnumerator.EnumAudioEndpoints(
        EDataFlow.eCapture.value, DEVICE_STATE.ACTIVE.value
    )

    count = collection.GetCount()
    for i in range(count):
        dev = collection.Item(i)
        if dev is not None:
            device = AudioUtilities.CreateDevice(dev)
            if not device or not device.FriendlyName:
                continue
            if device.FriendlyName.strip() == friendly_name.strip():
                return device.id
            
    return None