# INA219 전력 모니터링 시스템 아키텍처 설계

## 1. 시스템 개요

기존 아두이노 기반 INA219 전력 모니터링 시스템을 확장하여, 실시간 데이터를 중간 통신 계층을 통해 웹 기반 대시보드로 전송하는 단순한 구조.

## 2. 시스템 구성

```
Arduino (INA219) → Serial/WiFi → Python Backend → Dashboard
```

### 2.1 아두이노 계층
- 기존 코드 그대로 유지 (INA219 센서 데이터 수집)
- 추가: 시리얼 통신으로 데이터 전송 기능

### 2.2 중간 통신 계층 (Python Backend)
**역할**: 아두이노 데이터 수집 및 대시보드로 전달

**주요 컴포넌트**:
- **Serial Reader**: 아두이노에서 시리얼 데이터 수신
- **Data Parser**: JSON 형태로 데이터 변환
- **WebSocket Server**: 실시간 데이터 전송

**기술 스택**:
- Python + pySerial (시리얼 통신)
- FastAPI + WebSocket (실시간 통신)
- 간단한 메모리 기반 데이터 저장

### 2.3 대시보드 계층
**역할**: 실시간 데이터 시각화

**주요 기능**:
- 실시간 W/V/A 값 표시
- 간단한 그래프 (최근 60초)
- 현재 상태 인디케이터

**기술 스택**:
- HTML + JavaScript (Vanilla JS)
- Chart.js (그래프)
- WebSocket (실시간 데이터 수신)

## 3. 데이터 플로우

```
1. Arduino → Serial Port: {"w": 1.23, "v": 5.02, "a": 0.245, "timestamp": "..."}
2. Python Backend → Parse & Validate
3. Backend → WebSocket → Dashboard: Real-time update
```

## 4. 디렉토리 구조

```
src/
├── python/
│   ├── backend/
│   │   ├── serial_reader.py    # 아두이노 데이터 수집
│   │   ├── websocket_server.py # 실시간 데이터 전송
│   │   └── main.py             # 메인 서버
│   └── dashboard/
│       ├── app.py              # Flask/FastAPI 웹서버
│       ├── static/
│       │   ├── js/
│       │   │   └── dashboard.js # 대시보드 로직
│       │   └── css/
│       │       └── style.css   # 스타일
│       └── templates/
│           └── index.html      # 메인 대시보드
```

## 5. 간단한 구현 방안

### 5.1 Python Backend 핵심 로직
```python
# serial_reader.py - 아두이노 데이터 수집
import serial
import json

class SerialReader:
    def read_sensor_data(self):
        # 시리얼 포트에서 데이터 읽기
        # JSON 파싱
        # 유효성 검증
        return {"w": float, "v": float, "a": float}
```

### 5.2 WebSocket 실시간 통신
```python
# websocket_server.py
from fastapi import WebSocket

async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = serial_reader.get_latest_data()
        await websocket.send_json(data)
        await asyncio.sleep(0.1)  # 100ms 간격
```

### 5.3 Dashboard JavaScript
```javascript
// dashboard.js
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    updateValues(data.w, data.v, data.a);
    updateChart(data);
};
```

## 6. 최소 구현 우선순위

1. **Phase 1**: 아두이노 → Serial → Python 데이터 수집
2. **Phase 2**: Python → WebSocket → 웹페이지 실시간 표시
3. **Phase 3**: 간단한 그래프 추가
4. **Phase 4**: UI 개선 및 에러 처리

## 7. 장점

- **단순성**: 최소한의 컴포넌트
- **확장성**: 필요시 데이터베이스, 로깅 등 추가 가능
- **실시간**: WebSocket으로 즉시 데이터 반영
- **독립성**: 각 계층이 독립적으로 동작

## 8. 고려사항

- 아두이노 시리얼 포트 안정성
- WebSocket 연결 끊김 처리
- 브라우저 호환성 (Chrome, Firefox, Safari)
- 동시 사용자 제한 (단일 사용자 환경 가정)