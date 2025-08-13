# INA219 지능형 전력 모니터링 시스템

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.116.1-green.svg)
![Docker](https://img.shields.io/badge/docker-supported-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Tests](https://img.shields.io/badge/tests-passing-green.svg)

Arduino UNO R4 WiFi와 FastAPI를 활용한 **완전한 지능형 전력 모니터링 시스템**

## 🎯 프로젝트 개요

INA219 센서를 사용하여 전압, 전류, 전력을 실시간으로 측정하고, 고급 데이터 분석(이동평균, 이상치 탐지)을 수행하며, 웹 대시보드를 통해 시각화하는 **산업용 수준의 지능형 모니터링 시스템**입니다.

### ✨ 주요 기능

- **🤖 Arduino 시뮬레이터**: 실제 하드웨어 없이도 5가지 모드(정상, 부하 급증, 전압 강하 등)를 시뮬레이션하여 완벽한 개발 및 테스트 환경을 제공합니다.
- **📊 실시간 모니터링 대시보드**: Chart.js 기반의 멀티라인 실시간 그래프(전압, 전류, 전력)와 1분 통계 패널을 제공합니다.
- **💾 48시간 데이터 저장 및 분석**: SQLite를 사용하여 48시간 동안의 데이터를 저장하고, 히스토리 차트를 통해 시계열 분석 및 CSV 다운로드를 지원합니다.
- **🧠 지능형 데이터 분석**: 이동평균(1분/5분/15분) 및 Z-score & IQR 듀얼 이상치 탐지 엔진을 통해 데이터의 이상 징후를 실시간으로 분석하고 알립니다.
- **🐳 Docker 지원**: 멀티스테이지 Docker 빌드를 통해 개발, 테스트, 운영 환경을 분리하고, 35MB의 이미지를 최적화하여 효율적인 배포를 지원합니다.
- **🛡️ 보안 강화**: 운영 환경에서 API 문서를 비활성화하고, 안전한 예외 처리를 적용하여 시스템 보안을 강화했습니다.
- **✅ 높은 코드 품질**: Ruff와 Black을 이용한 자동 코드 포맷팅 및 품질 검사를 통해 900개 이상의 이슈를 해결하여 코드의 일관성과 안정성을 확보했습니다.

## 🛠️ 기술 스택

### 🔧 Hardware
- **Arduino UNO R4 WiFi**
- **INA219 센서**

### 💻 Backend
- **Python 3.9+**
- **FastAPI 0.116.1**
- **Uvicorn**
- **WebSocket**
- **SQLite**
- **NumPy**
- **pySerial**

### 🌐 Frontend
- **Chart.js 4.4.4**
- **HTML5/CSS3/JavaScript**

### 🐳 DevOps & 배포
- **Docker** & **Docker Compose**
- **GitHub Actions**

### 🔍 개발 도구 & 품질 관리
- **Ruff + Black**
- **MyPy**
- **Pytest**
- **TruffleHog**

## 🚀 빠른 시작

### 📦 방법 1: Docker로 즉시 실행 (권장)

```bash
# 1. 저장소 클론
git clone https://github.com/koreatogether/03_P_ina219_powerMonitoring.git
cd 03_P_ina219_powerMonitoring

# 2. Docker Compose로 운영 서비스 실행
docker-compose up ina219-monitor

# 3. 브라우저에서 접속
open http://localhost:8000
```

### 🐍 방법 2: Python 직접 실행

```bash
# 1. 의존성 설치
pip install -r src/python/backend/requirements.txt

# 2. 백엔드 서버 실행
python src/python/backend/main.py

# 3. 웹 대시보드 접속
open http://localhost:8000
```

### 🎮 Arduino 시뮬레이터 (하드웨어 없이 테스트)

```bash
# 기본 30초 테스트
python src/python/simulator/test_simulator.py

# Mock 시뮬레이터만 사용
python src/python/simulator/test_simulator.py --mock
```

## 📁 프로젝트 구조

```
src/
├── arduino/
│   ├── uno_r4_wifi_ina219_simulator.ino     # JSON 기반 시뮬레이터
│   └── README.md
├── python/
│   ├── simulator/                            # Phase 1: 시뮬레이터 패키지
│   │   ├── __init__.py
│   │   ├── arduino_mock.py
│   │   ├── simulator_interface.py
│   │   └── test_simulator.py
│   └── backend/                              # Phase 2-4: 웹 백엔드 시스템
│       ├── main.py                           # FastAPI 메인 서버
│       ├── database.py
│       ├── requirements.txt
│       └── requirements-dev.txt
└── docs/
    ├── architecture/
    └── release.md
```

## 🧪 테스트

### Docker 기반 테스트 (권장)
```bash
# 전체 테스트 실행
docker-compose -f docker-compose.test.yml up --build
```

### 로컬 테스트
```bash
# 개발 의존성 설치
pip install -r src/python/backend/requirements-dev.txt

# Pytest 실행
pytest
```

## 🔄 업데이트 로그

### v4.2.1 (2025-08-13)
- **보안 강화**: 운영 환경 API 문서 비활성화, 안전한 예외 처리 적용.
- **코드 품질 개선**: Ruff/Black 자동화를 통해 936개 이슈 해결.
- **품질 검사 시스템**: 프로젝트 특화 코드 품질 및 보안 스캔 도구 완성.

### v4.2.0 (2025-08-13)
- **Docker 컨테이너화**: 멀티 스테이지 빌드로 운영/개발 환경 분리 및 35MB 이미지 최적화.
- **의존성 최적화**: 운영용 패키지를 12개에서 7개로 42% 감소.

### v4.1.0 (2025-08-13)
- **지능형 분석 시스템**: 이동평균 및 Z-score/IQR 이상치 탐지 기능 구현.
- **시스템 안정화**: FastAPI 최신 표준 적용 및 주요 버그 해결.

*상세한 릴리즈 내역은 `docs/release.md` 파일을 참고하세요.*

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.
