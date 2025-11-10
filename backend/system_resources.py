"""
시스템 리소스 모니터링 유틸리티
"""
import psutil
import subprocess
from typing import Dict

def get_system_resources() -> Dict:
    """시스템 리소스 사용량을 반환합니다."""
    try:
        # CPU 사용률
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # 메모리 사용량
        memory = psutil.virtual_memory()
        memory_total_gb = memory.total / (1024 ** 3)
        memory_used_gb = memory.used / (1024 ** 3)
        memory_percent = memory.percent
        memory_available_gb = memory.available / (1024 ** 3)
        
        # 디스크 사용량
        disk = psutil.disk_usage('/')
        disk_total_gb = disk.total / (1024 ** 3)
        disk_used_gb = disk.used / (1024 ** 3)
        disk_percent = disk.percent
        disk_free_gb = disk.free / (1024 ** 3)
        
        # 실행 중인 Docker 컨테이너 수
        try:
            result = subprocess.run(
                "docker ps --format '{{.Names}}' | wc -l",
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            docker_containers = int(result.stdout.strip()) if result.returncode == 0 else 0
        except Exception:
            docker_containers = 0
        
        # 실행 중인 MICA Pipeline 컨테이너 수
        try:
            result = subprocess.run(
                "docker ps --filter 'name=sub-' --format '{{.Names}}' | wc -l",
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            mica_containers = int(result.stdout.strip()) if result.returncode == 0 else 0
        except Exception:
            mica_containers = 0
        
        return {
            "success": True,
            "cpu": {
                "percent": round(cpu_percent, 1),
                "count": cpu_count,
                "available": cpu_count
            },
            "memory": {
                "total_gb": round(memory_total_gb, 2),
                "used_gb": round(memory_used_gb, 2),
                "available_gb": round(memory_available_gb, 2),
                "percent": round(memory_percent, 1)
            },
            "disk": {
                "total_gb": round(disk_total_gb, 2),
                "used_gb": round(disk_used_gb, 2),
                "free_gb": round(disk_free_gb, 2),
                "percent": round(disk_percent, 1)
            },
            "docker": {
                "total_containers": docker_containers,
                "mica_containers": mica_containers
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

