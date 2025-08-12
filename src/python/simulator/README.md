# Arduino INA219 Python Simulator

Arduino UNO R4 WiFi + INA219 전력 모니터링 시스템의 Python 기반 시뮬레이터 패키지입니다.

## 📦 패키지 구성

```
simulator/
├── __init__.py              # 패키지 초기화
├── arduino_mock.py          # Mock 시뮬레이터 구현
├── simulator_interface.py   # 통합 인터페이스
├── test_simulator.py        # 테스트 스크립트
└── README.md               # 이 문서
```

## ✨ 주요 특징

- 🔧 **실제 Arduino와 Mock 시뮬레이터 통합 지원**
- 📡 **JSON 프로토콜 완벽 호환**
- 🎭 **다양한 시뮬레이션 모드**
- 🔄 **자동 포트 감지 및 폴백**
- 📊 **실시간 데이터 생성**
- 🛡️ **데이터 무결성 검증**
- 🔌 **자동 재연결 기능**

## 🚀 빠른 시작

### 기본 사용법

```python
from simulator import create_simulator

# 자동 감지 (실제 Arduino 우선, Mock 폴백)
sim = create_simulator("AUTO")

if sim.connect():
    print(f"Connected using {sim.get_simulator_type()} simulator")
    
    # 데이터 읽기
    data = sim.read_data()
    if data:
        print(f"Received: {data}")
    
    # 명령 전송
    sim.send_command('{"cmd":"get_status","seq":1}')
    
    sim.disconnect()
```

### Mock 시뮬레이터만 사용

```python
from simulator import create_simulator

# Mock 시뮬레이터 강제 사용
sim = create_simulator("MOCK")

if sim.connect():
    # 콜백 함수 설정
    def on_data(data):
        print(f"V={data['v']}V, A={data['a']}A, W={data['w']}W")
    
    sim.set_data_callback(on_data)
    
    # 10초간 데이터 수집
    import time
    time.sleep(10)
    
    sim.disconnect()
```

### 특정 포트 사용

```python
from simulator import create_simulator, list_available_ports

# 사용 가능한 포트 확인
list_available_ports()

# 특정 포트 사용
sim = create_simulator("COM3")  # Windows
# sim = create_simulator("/dev/ttyUSB0")  # Linux
```

## 🎭 시뮬레이션 모드

### 지원 모드

| 모드 | 설명 | 전압 범위 | 전류 범위 | 용도 |
|------|------|-----------|-----------|------|
| `NORMAL` | 정상 동작 | 4.95-5.05V | 0.18-0.32A | 기본 테스트 |
| `LOAD_SPIKE` | 부하 급증 | 4.5-4.7V | 0.8-1.0A | 과부하 테스트 |
| `VOLTAGE_DROP` | 전압 강하 | 4.1-4.3V | 0.3-0.4A | 전원 불안정 |
| `NOISE` | 노이즈 환경 | 4.8-5.2V | 0.1-0.3A | 노이즈 내성 |
| `ERROR_TEST` | 센서 오류 | -1.0V | -1.0A | 에러 처리 |

### 모드 변경

```python
# JSON 명령으로 모드 변경
sim.send_command('{"cmd":"set_mode","value":"LOAD_SPIKE","seq":1}')

# Mock 시뮬레이터 직접 제어
if sim.get_simulator_type() == "Mock":
    mock_sim = sim.simulator.mock_sim
    mock_sim.current_mode = SimulationMode.NOISE
```

## 📡 통신 프로토콜

### 데이터 포맷

#### 측정 데이터
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

#### 상태 메시지
```json
{
  "type": "status",
  "message": "Simulator ready",
  "ts": 1712345678
}
```

#### 명령 응답
```json
{
  "ack": 123,
  "result": "ok",
  "message": "Command executed"
}
```

## 🔧 고급 사용법

### 콜백 함수 활용

```python
from simulator import create_simulator
import json

sim = create_simulator("AUTO")

# 데이터 수신 콜백
def on_measurement_data(data):
    print(f"Power: {data['w']:.3f}W")
    
    # 임계값 체크
    if data['w'] > 2.0:
        print("⚠️ High power consumption!")

# 상태 메시지 콜백
def on_status_message(message):
    print(f"📢 {message}")

# 연결 상태 콜백
def on_connection_change(connected, info):
    status = "Connected" if connected else "Disconnected"
    print(f"🔌 {status}: {info}")

# 콜백 등록
sim.set_data_callback(on_measurement_data)
sim.set_status_callback(on_status_message)
sim.set_connection_callback(on_connection_change)

if sim.connect():
    # 실시간 모니터링
    import time
    time.sleep(30)
    sim.disconnect()
```

### 설정 커스터마이징

```python
from simulator import SimulatorManager, SimulatorConfig

# 커스텀 설정
config = SimulatorConfig(
    port="AUTO",
    baudrate=115200,
    timeout=2.0,
    auto_reconnect=True,
    mock_fallback=True
)

sim = SimulatorManager(config)
```

### 데이터 수집 및 분석

```python
import json
import time
from collections import deque

sim = create_simulator("AUTO")
data_buffer = deque(maxlen=100)  # 최근 100개 데이터

def collect_data(data):
    data_buffer.append(data)
    
    # 통계 계산
    if len(data_buffer) >= 10:
        powers = [d['w'] for d in data_buffer]
        avg_power = sum(powers) / len(powers)
        max_power = max(powers)
        min_power = min(powers)
        
        print(f"Power Stats: Avg={avg_power:.3f}W, "
              f"Min={min_power:.3f}W, Max={max_power:.3f}W")

sim.set_data_callback(collect_data)

if sim.connect():
    time.sleep(60)  # 1분간 데이터 수집
    sim.disconnect()
    
    # 수집된 데이터 분석
    print(f"Total samples collected: {len(data_buffer)}")
```

## 🧪 테스트 도구

### 기본 테스트 실행

```bash
# 기본 30초 테스트
python test_simulator.py

# Mock 시뮬레이터만 사용
python test_simulator.py --mock

# 특정 포트 사용
python test_simulator.py --port COM3

# 테스트 시간 변경
python test_simulator.py --duration 60

# 사용 가능한 포트 목록
python test_simulator.py --list-ports
```

### 테스트 결과 예시

```
=== Arduino Simulator Test ===
Port: AUTO
Duration: 30 seconds
========================================

📡 Basic Connection Test
------------------------------
✅ Connection status: OK
📊 Reading initial data...
  Sample 1: {"v":5.023,"a":0.234,"w":1.175,"ts":1712345678,"seq":1,"status":"ok","mode":"NORMAL"}...
  Sample 2: {"v":5.018,"a":0.241,"w":1.209,"ts":1712345679,"seq":2,"status":"ok","mode":"NORMAL"}...
  Sample 3: {"v":5.031,"a":0.228,"w":1.147,"ts":1712345680,"seq":3,"status":"ok","mode":"NORMAL"}...

🎮 Command Test
------------------------------
  📤 Status query
    ✅ Command sent
    📥 Response: ok
  📤 Set interval to 500ms
    ✅ Command sent
    📥 Response: ok

📈 Data Collection Test (30s)
------------------------------
  ⏱️  5s elapsed, 25s remaining | Data: 47, Errors: 0
  ⏱️ 10s elapsed, 20s remaining | Data: 94, Errors: 0
  ⏱️ 15s elapsed, 15s remaining | Data: 141, Errors: 0
  ⏱️ 20s elapsed, 10s remaining | Data: 188, Errors: 0
  ⏱️ 25s elapsed,  5s remaining | Data: 235, Errors: 0
  ⏱️ 30s elapsed,  0s remaining | Data: 282, Errors: 0

📊 Test Results
========================================
📈 Data Statistics:
  Total samples: 282
  Error count: 0
  Data rate: 9.4 samples/sec
  Error rate: 0.0%

⚡ Measurement Statistics:
  Voltage: 4.951V - 5.049V (avg: 5.001V)
  Current: 0.182A - 0.318A (avg: 0.242A)
  Power: 0.901W - 1.605W (avg: 1.211W)

✅ Test PASSED
```

## 🔍 문제 해결

### 연결 문제

```python
from simulator import list_available_ports

# 1. 사용 가능한 포트 확인
list_available_ports()

# 2. 특정 포트로 직접 연결 시도
sim = create_simulator("COM3")  # 실제 포트명 사용

# 3. Mock 시뮬레이터로 폴백
sim = create_simulator("MOCK")
```

### 데이터 수신 문제

```python
# 타임아웃 증가
data = sim.read_data(timeout=5.0)

# 연결 상태 확인
if not sim.is_connected():
    print("Connection lost, reconnecting...")
    sim.connect()
```

### 성능 최적화

```python
# 비동기 데이터 처리
import threading
import queue

data_queue = queue.Queue()

def data_collector():
    while True:
        data = sim.read_data(timeout=0.1)
        if data:
            data_queue.put(data)

# 별도 스레드에서 데이터 수집
collector_thread = threading.Thread(target=data_collector, daemon=True)
collector_thread.start()

# 메인 스레드에서 데이터 처리
while True:
    try:
        data = data_queue.get(timeout=1.0)
        # 데이터 처리 로직
        process_data(data)
    except queue.Empty:
        continue
```

## 📚 API 참조

### SimulatorManager

#### 메서드
- `connect() -> bool` - 시뮬레이터 연결
- `disconnect()` - 연결 해제
- `send_command(command: str) -> bool` - 명령 전송
- `read_data(timeout: float) -> Optional[str]` - 데이터 읽기
- `is_connected() -> bool` - 연결 상태 확인
- `get_simulator_type() -> str` - 시뮬레이터 타입 반환

#### 콜백 설정
- `set_data_callback(callback)` - 데이터 수신 콜백
- `set_status_callback(callback)` - 상태 메시지 콜백
- `set_connection_callback(callback)` - 연결 상태 콜백

### ArduinoMockSimulator

#### 메서드
- `connect() -> bool` - Mock 시뮬레이터 시작
- `disconnect()` - Mock 시뮬레이터 중지
- `send_command(command: str) -> bool` - 명령 전송
- `read_data(timeout: float) -> Optional[str]` - 데이터 읽기

#### 속성
- `current_mode: SimulationMode` - 현재 시뮬레이션 모드
- `measurement_interval: int` - 측정 주기 (ms)
- `sequence_number: int` - 현재 시퀀스 번호

## 🔗 관련 문서

- [Arduino 시뮬레이터 README](../arduino/README.md)
- [아키텍처 문서](../../docs/architecture/)
- [백엔드 구현](../backend/)

---

**참고**: 이 시뮬레이터는 개발 및 테스트 목적으로 설계되었습니다. 프로덕션 환경에서는 실제 Arduino 하드웨어를 사용하세요.