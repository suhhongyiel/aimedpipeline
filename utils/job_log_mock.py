# utils/job_log_mock.py (새 파일로 만들어도 되고, run_pipeline.py 위쪽에 써도 됨)
import time
import random

def get_mock_log(progress):
    """진행률에 따라 다른 log 메시지를 리턴"""
    logs = [
        "[INFO] 자료 업로드 중...",
        "[INFO] 전처리 중...",
        "[INFO] 모델 예측 시작...",
        "[WARNING] 신뢰도 낮은 샘플 발견!",
        "[INFO] 후처리 및 리포트 생성 중...",
        "[SUCCESS] 결과 파일 생성 완료!"
    ]
    # 진행률에 따라 적절히 log 반환
    idx = int(progress // (100 / len(logs)))
    idx = min(idx, len(logs)-1)
    return logs[idx]
