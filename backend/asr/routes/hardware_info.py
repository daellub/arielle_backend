# backend/asr/routes/hardware_info.py
import platform
import psutil
import subprocess
import os
from fastapi import APIRouter

def get_cpu_name():
    try:
        if platform.system() == "Windows":
            result = subprocess.check_output(
                ['powershell', '-Command', 'Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Name']
            ).decode().strip()
            return result
        elif platform.system() == "Linux":
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        return line.split(":")[1].strip()
        elif platform.system() == "Darwin":
            result = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"]).decode()
            return result.strip()
    except Exception as e:
        print("[ERROR] CPU 이름 감지 실패:", e)
    return platform.processor() or "알 수 없음"

router = APIRouter()

@router.get("/hardware/info")
def get_hardware_info():
    cpu_name = get_cpu_name()
    cpu_usage = psutil.cpu_percent(interval=0.1)

    ram = psutil.virtual_memory()
    ram_total_gb = f'{round(ram.total / (1024 ** 3))}GB'
    ram_used_percent = f'{ram.percent}%'

    disk = psutil.disk_usage('/')
    disk_total_gb = f'{round(disk.total / (1024 ** 3))}GB'
    disk_used_percent = f'{disk.percent}%'

    return {
        'cpu': cpu_name,
        'cpu_usage': f'{cpu_usage}%',
        'ram': {
            'total': ram_total_gb,
            'used_percent': ram_used_percent
        },
        'disk': {
            'total': disk_total_gb,
            'used_percent': disk_used_percent
        }
    }