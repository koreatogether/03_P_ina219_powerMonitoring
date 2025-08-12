# Arduino UNO R4 WiFi + INA219 시뮬레이터

Arduino UNO R4 WiFi 기반 INA219 전력 모니터링 시스템의 시뮬레이터입니다.

## 📁 파일 구성

### Arduino 코드
- `arduino.ino` - 기존 INA219 기본 구현 (CSV 포맷)
- `uno_r4_wifi_ina219_simulator.ino` - **새로운 JSON 기반 시뮬레이터**

### 주요 특징

#### `uno_r4_wifi_ina219_simulator.ino`
- ✅ **JSON 프로토콜** 지원
- ✅ **시퀀스 번호** 기반 데이터 무결성
- ✅ **ACK/NACK** 응답 시스템
- ✅ **다양한 시뮬레이션 모드**
- ✅ **명령 수신 및 처리**
- ✅ **실제 하드웨어 없이도 동작**

## 🔧 하드웨어 요구사항

### 실제 하드웨어 구성
```
Arduino UNO R4 WiFi
├── INA219 전력 센서
│   ├── VCC → 3.3V 또는 5V
│   ├── GND → GND
│   ├── SDA → A4 (I2C 데이터)
│   └── SCL → A5 (I2C 클럭)
└── USB 연결 (시리얼 통신)
```

### 시뮬레이터 모드
- 실제 INA219 센서 없이도 동작
- Mock 데이터 생성으로 다양한 시나리오 테스트
- 개발 환경에서 하드웨어 의존성 제거

## 📡 통신 프로토콜

### JSON 데이터 포맷

#### 측정 데이터 (Arduino → PC)
```json
{
  "v": 5.02,           // 전압 (V)
  "a": 0.245,          // 전류 (A)
  "w": 1.23,           // 전력 (W)
  "ts": 1712345678,    // 타임스탬프 (ms)
  "seq": 123,          // 시퀀스 번호
  "status": "ok",      // 센서 상태
  "mode": "NORMAL"     // 시뮬레이션 모드
}
```

#### 명령 전송 (PC → Arduino)
```json
{
  "cmd": "set_interval",
  "value": 500,        // 측정 주기 (ms)
  "seq": 124
}
```

#### 응답 (Arduino → PC)
```json
{
  "ack": 124,
  "result": "ok",
  "message": "Interval updated"
}
```

### 지원 명령어

#### JSON 명령
- `set_interval` - 측정 주기 설정 (100-10000ms)
- `set_mode` - 시뮬레이션 모드 변경
- `get_status` - 시스템 상태 조회
- `reset` - 시스템 리셋

#### 텍스트 명령
- `HELP` - 도움말 출력
- `STATUS` - 상태 정보 출력
- `MODES` - 시뮬레이션 모드 목록

## 🎭 시뮬레이션 모드

### NORMAL
- 정상 동작 시뮬레이션
- 기준값 ± 작은 노이즈
- 사인파 패턴 전류 변화

### LOAD_SPIKE
- 부하 급증 상황
- 전압 강하 + 전류 증가
- 전력 스파이크 시뮬레이션

### VOLTAGE_DROP
- 전압 강하 상황
- 4.2V 수준으로 전압 감소
- 보상 전류 증가

### NOISE
- 노이즈가 많은 환경
- 큰 폭의 랜덤 변동
- 측정 불안정성 시뮬레이션

### ERROR_TEST
- 센서 오류 상황
- 비정상 값 (-1.0) 출력
- 에러 처리 테스트용

## 🚀 사용법

### 1. Arduino IDE 설정
```cpp
// 필요한 라이브러리
#include <ArduinoJson.h>  // JSON 처리
#include <WiFiS3.h>       // UNO R4 WiFi 전용
```

### 2. 업로드 및 실행
1. Arduino IDE에서 `uno_r4_wifi_ina219_simulator.ino` 열기
2. 보드: "Arduino UNO R4 WiFi" 선택
3. 포트 선택 후 업로드
4. 시리얼 모니터 열기 (115200 baud)

### 3. 시리얼 모니터에서 테스트
```
// 상태 확인
STATUS

// 모드 변경
{"cmd":"set_mode","value":"LOAD_SPIKE","seq":1}

// 측정 주기 변경
{"cmd":"set_interval","value":500,"seq":2}
```

## 🔍 문제 해결

### 연결 문제
- USB 케이블 확인
- 드라이버 설치 확인
- 포트 번호 확인

### 라이브러리 오류
```bash
# Arduino IDE에서 라이브러리 설치
Tools → Manage Libraries
- ArduinoJson (by Benoit Blanchon)
```

### 시리얼 통신 문제
- Baud rate: 115200 확인
- Line ending: "Newline" 설정
- 버퍼 오버플로우 시 Arduino 리셋

## 📊 성능 특성

### 기본 설정
- 측정 주기: 1초 (1000ms)
- 시리얼 속도: 115200 baud
- JSON 패킷 크기: ~150 bytes

### 성능 지표
- 최대 데이터 레이트: ~10 samples/sec
- 지연 시간: <100ms
- 메모리 사용량: ~2KB RAM

## 🔗 Python 연동

이 Arduino 시뮬레이터는 `src/python/simulator/` 패키지와 완벽 호환됩니다:

```python
from simulator import create_simulator

# 실제 Arduino 연결
sim = create_simulator("COM3")

# 또는 자동 감지
sim = create_simulator("AUTO")

if sim.connect():
    data = sim.read_data()
    print(data)
```

## 📝 개발 노트

### 아키텍처 준수
- JSON 프로토콜 (아키텍처 문서 3.1절)
- 시퀀스 번호 무결성 (아키텍처 문서 4.1절)
- ACK/NACK 시스템 (아키텍처 문서 4.2절)
- 다양한 시뮬레이션 모드 지원

### 확장 가능성
- 새로운 센서 추가 용이
- 통신 프로토콜 확장 가능
- 시뮬레이션 모드 추가 가능

---

**참고**: 실제 프로덕션 환경에서는 `arduino.ino` 대신 이 시뮬레이터를 기반으로 실제 INA219 센서 코드를 통합하여 사용하세요.