"""
리소스 기반 스케줄링을 위한 유틸리티
시스템 리소스(CPU, 메모리)에 따라 동적으로 작업 할당량을 조절합니다.
"""
import psutil
import subprocess
from typing import Dict, Optional

def check_system_resources() -> Dict:
    """시스템 리소스 상태를 확인하고 작업 할당 가능 여부를 반환합니다."""
    try:
        # CPU 사용률 및 코어 수
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_available = cpu_count * (1 - cpu_percent / 100)
        
        # 메모리 사용량
        memory = psutil.virtual_memory()
        memory_total_gb = memory.total / (1024 ** 3)
        memory_available_gb = memory.available / (1024 ** 3)
        memory_percent = memory.percent
        
        # 실행 중인 Docker 컨테이너 수
        try:
            result = subprocess.run(
                "docker ps --format '{{.Names}}' | wc -l",
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            running_containers = int(result.stdout.strip()) if result.returncode == 0 else 0
        except Exception:
            running_containers = 0
        
        # 리소스 기반 작업 할당량 계산
        # CPU 기반: 사용 가능한 CPU 코어 수에 따라 작업 수 결정
        # 메모리 기반: 사용 가능한 메모리에 따라 작업 수 결정 (각 작업당 약 4GB 가정)
        # 안전 마진: 리소스의 80%까지만 사용
        
        # CPU 기반 최대 작업 수 (안전 마진 80%)
        max_tasks_by_cpu = max(1, int(cpu_available * 0.8))
        
        # 메모리 기반 최대 작업 수 (각 작업당 4GB 가정, 안전 마진 80%)
        memory_per_task_gb = 4.0
        max_tasks_by_memory = max(1, int((memory_available_gb * 0.8) / memory_per_task_gb))
        
        # 두 값 중 작은 값을 사용 (병목 방지)
        recommended_max_tasks = min(max_tasks_by_cpu, max_tasks_by_memory)
        
        # 최소값 보장 (최소 1개 작업은 실행 가능)
        recommended_max_tasks = max(1, recommended_max_tasks)
        
        return {
            "success": True,
            "cpu": {
                "percent": round(cpu_percent, 1),
                "count": cpu_count,
                "available": round(cpu_available, 1)
            },
            "memory": {
                "total_gb": round(memory_total_gb, 2),
                "available_gb": round(memory_available_gb, 2),
                "percent": round(memory_percent, 1)
            },
            "running_containers": running_containers,
            "recommended_max_tasks": recommended_max_tasks,
            "max_tasks_by_cpu": max_tasks_by_cpu,
            "max_tasks_by_memory": max_tasks_by_memory,
            "can_run_more": memory_percent < 90 and cpu_percent < 90
        }
    except Exception as e:
        # 에러 발생 시 기본값 반환
        return {
            "success": False,
            "error": str(e),
            "recommended_max_tasks": 2,  # 안전한 기본값
            "can_run_more": True
        }

def get_resource_pool_slots() -> int:
    """시스템 리소스에 기반하여 리소스 풀 슬롯 수를 반환합니다."""
    resources = check_system_resources()
    if resources.get("success"):
        return resources.get("recommended_max_tasks", 2)
    return 2  # 기본값

