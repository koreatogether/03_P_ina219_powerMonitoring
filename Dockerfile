# INA219 Power Monitoring System - Production Docker Image
# Phase 4.1: Intelligent Data Analysis System

# 멀티 스테이지 빌드 - 최적화된 운영 이미지
FROM python:3.11-slim as base

# 시스템 패키지 업데이트 및 필수 도구 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# Python 환경 최적화
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONIOENCODING=utf-8

# 운영용 의존성만 설치 (최적화)
COPY src/python/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY src/python/simulator/ ./simulator/
COPY src/python/backend/ ./backend/

# 데이터 디렉토리 생성
RUN mkdir -p /app/data/logs

# 포트 노출
EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/status || exit 1

# 서버 실행
CMD ["python", "backend/main.py"]

# 개발용 스테이지
FROM base as development

# 개발용 의존성 추가 설치
COPY src/python/backend/requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

# 개발용 볼륨 마운트 포인트
VOLUME ["/app/data", "/app/logs"]

# 개발 서버 실행 (리로드 활성화)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]