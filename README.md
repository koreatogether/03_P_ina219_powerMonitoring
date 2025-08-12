# INA219 Power Monitoring System

Arduino와 Dash를 활용한 실시간 전력 모니터링 시스템

## 🎯 프로젝트 개요

INA219 센서를 사용하여 전압, 전류, 전력을 실시간으로 측정하고 웹 대시보드를 통해 시각화하는 시스템입니다.

### 주요 기능

- **실시간 전력 측정**: INA219 센서를 통한 정확한 전압/전류/전력 측정
- **웹 대시보드**: Dash를 활용한 실시간 데이터 시각화
- **데이터 로깅**: 측정 데이터의 저장 및 분석
- **다중 플랫폼 지원**: Arduino Uno, Nano, ESP32 지원
- **성능 모니터링**: 시스템 성능 분석 및 최적화

## 🛠️ 기술 스택

### Hardware
- **Arduino**: Uno, Nano, ESP32
- **센서**: INA219 전력 측정 센서
- **통신**: I2C, Serial

### Software
- **Python**: 데이터 처리 및 대시보드
- **Arduino C++**: 펌웨어
- **Dash**: 웹 대시보드 프레임워크
- **PlatformIO**: 임베디드 개발 환경

### 개발 도구
- **uv**: Python 패키지 관리
- **Ruff**: 코드 린팅 및 포맷팅
- **MyPy**: 타입 검사
- **Pytest**: 테스트 프레임워크
- **Pre-commit**: Git hooks

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 프로젝트 클론
git clone <repository-url>
cd 03_P_ina219_powerMonitoring

# 개발 환경 자동 설정
python tools/setup_dev_environment.py

# 또는 수동 설정
python -m uv sync --extra dev
```

### 2. 빠른 환경 검증

```bash
python tools/quick_test.py
```

### 3. Arduino 펌웨어 업로드

```bash
# Arduino Uno용
pio run -e uno -t upload

# ESP32용
pio run -e esp32 -t upload
```

### 4. 대시보드 실행

```bash
python -m uv run python src/python/dashboard/app.py
```

## 📁 프로젝트 구조

```
03_P_ina219_powerMonitoring/
├── src/
│   ├── arduino/                 # Arduino 펌웨어
│   │   ├── main.ino            # 메인 Arduino 코드
│   │   └── lib/                # 라이브러리
│   ├── python/
│   │   ├── dashboard/          # Dash 웹 대시보드
│   │   │   ├── app.py         # 메인 대시보드 앱
│   │   │   ├── components/    # UI 컴포넌트
│   │   │   └── callbacks/     # 대시보드 콜백
│   │   └── data_processing/   # 데이터 처리 모듈
│   │       ├── collector.py   # 데이터 수집
│   │       ├── analyzer.py    # 데이터 분석
│   │       └── storage.py     # 데이터 저장
│   └── ina219_power_monitoring/ # Python 패키지
├── tests/                      # 테스트 코드
├── tools/                      # 개발 도구
│   ├── setup_dev_environment.py
│   ├── quick_test.py
│   ├── code_quality_checker.py
│   ├── build_and_test.py
│   ├── performance_analyzer.py
│   └── run_all_checks.py
├── docs/                       # 문서
├── benchmarks/                 # 성능 벤치마크
├── data/                       # 데이터 파일
│   ├── raw/                   # 원시 데이터
│   └── processed/             # 처리된 데이터
├── logs/                       # 로그 파일
├── pyproject.toml             # Python 프로젝트 설정
├── platformio.ini             # PlatformIO 설정
└── README.md
```

## 🔧 개발 도구 사용법

### 전체 검사 실행
```bash
python tools/run_all_checks.py
```

### 개별 도구 실행
```bash
# 코드 품질 검사
python tools/code_quality_checker.py

# 빌드 및 테스트
python tools/build_and_test.py

# 성능 분석
python tools/performance_analyzer.py
```

## 📊 하드웨어 연결

### INA219 연결도
```
Arduino Uno/Nano    INA219
GND        ------>  GND
5V         ------>  VCC
A4 (SDA)   ------>  SDA
A5 (SCL)   ------>  SCL
```

### ESP32 연결도
```
ESP32      INA219
GND   ---> GND
3.3V  ---> VCC
21    ---> SDA
22    ---> SCL
```

## 📈 사용 예시

### 1. 기본 전력 측정
```python
from src.python.data_processing.collector import PowerCollector

collector = PowerCollector(port='COM3')  # Windows
# collector = PowerCollector(port='/dev/ttyUSB0')  # Linux

data = collector.collect_data(duration=60)  # 60초간 데이터 수집
print(f"평균 전력: {data['power'].mean():.2f}W")
```

### 2. 실시간 모니터링
```python
from src.python.dashboard.app import app

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8050)
```

## 🧪 테스트

### 단위 테스트 실행
```bash
python -m uv run pytest tests/ -v
```

### 성능 벤치마크
```bash
python -m uv run python benchmarks/power_measurement_benchmark.py
```

## 📋 요구사항

### 하드웨어
- Arduino Uno/Nano 또는 ESP32
- INA219 전력 측정 센서
- USB 케이블
- 점퍼 와이어

### 소프트웨어
- Python 3.9+
- PlatformIO
- Git

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 📞 지원

문제가 발생하거나 질문이 있으시면 다음을 확인해주세요:

1. **빠른 진단**: `python tools/quick_test.py`
2. **로그 확인**: `logs/` 디렉토리의 최신 로그 파일
3. **문서**: `docs/` 디렉토리의 상세 문서
4. **이슈 등록**: GitHub Issues

## 🔄 업데이트 로그

### v0.1.0 (2025-08-12)
- 초기 프로젝트 설정
- uv 기반 개발 환경 구축
- 기본 도구 체인 구성
- Arduino 및 Python 통합 환경