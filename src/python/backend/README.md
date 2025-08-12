# INA219 Power Monitoring Backend

Phase 2.1: WebSocket 실시간 통신 최소 구현

## 🎯 구현 목표

Phase 2의 첫 번째 단계로 **WebSocket 실시간 통신**만 최소한으로 구현하여 단계별 테스트를 진행합니다.

## ✨ 구현된 기능

### 1. FastAPI 기본 서버
- REST API 엔드포인트
- 시스템 상태 조회
- 시뮬레이터 제어

### 2. WebSocket 실시간 통신
- 클라이언트 연결 관리
- 실시간 데이터 브로드캐스팅
- 연결 상태 모니터링

### 3. 시뮬레이터 통합
- Mock 시뮬레이터 자동 연결
- JSON 데이터 실시간 전송
- 상태 메시지 브로드캐스트

## 🚀 빠른 시작

### 1. 의존성 설치

```bash
# 백엔드 디렉토리로 이동
cd src/python/backend

# 의존성 설치
pip install -r requirements.txt
```

### 2. 서버 실행

```bash
# 개발 서버 실행 (자동 리로드)
python main.py

# 또는 uvicorn 직접 실행
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

서버가 시작되면 다음 주소들을 사용할 수 있습니다:
- **API 문서**: http://localhost:8000/docs
- **서버 상태**: http://localhost:8000/status
- **WebSocket**: ws://localhost:8000/ws

### 3. 테스트 실행

#### 자동 테스트
```bash
# 종합 테스트 실행
python test_phase2.py
```

#### 웹 브라우저 테스트
```bash
# 브라우저에서 열기
open test_websocket.html
# 또는 직접 파일을 브라우저로 드래그
```

## 📡 API 엔드포인트

### REST API

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/` | 루트 페이지 |
| `GET` | `/status` | 시스템 상태 조회 |
| `POST` | `/simulator/start` | 시뮬레이터 시작 |
| `POST` | `/simulator/stop` | 시뮬레이터 중지 |

### WebSocket

| 경로 | 설명 |
|------|------|
| `/ws` | 실시간 데이터 스트림 |

## 📊 WebSocket 메시지 포맷

### 측정 데이터
```json
{
  "type": "measurement",
  "data": {
    "v": 5.02,
    "a": 0.245,
    "w": 1.23,
    "ts": 1712345678,
    "seq": 123,
    "status": "ok",
    "mode": "NORMAL"
  },
  "timestamp": "2025-08-13T10:30:45.123456"
}
```

### 상태 메시지
```json
{
  "type": "status",
  "message": "Simulator ready - Starting measurements...",
  "timestamp": "2025-08-13T10:30:45.123456"
}
```

## 🧪 테스트 결과 예시

```
🧪 Phase 2.1 WebSocket Real-time Communication Test
============================================================

🔬 Running Server Status test...
✅ Server status: {'server': 'running', 'simulator': 'connected', 'websocket_connections': 0}
✅ Server Status test PASSED

🔬 Running WebSocket Connection test...
🔗 Testing WebSocket connection to ws://localhost:8000/ws...
✅ WebSocket connected successfully
📊 Data: V=5.023V, A=0.234V, W=1.175W
📊 Data: V=5.018V, A=0.241V, W=1.209W
✅ WebSocket test completed. Messages received: 8
✅ WebSocket Connection test PASSED

🔬 Running Simulator Integration test...
🎭 Testing simulator integration...
✅ Simulator start response: {'status': 'started', 'type': 'Mock'}
📡 Testing real-time data stream...
  📈 Sample 1: V=4.995V, A=0.267V, W=1.335W, Seq=1
  📈 Sample 2: V=5.001V, A=0.282V, W=1.410W, Seq=2
✅ Received 10 measurement samples
✅ Simulator Integration test PASSED

🔬 Running Performance test...
🚀 Testing performance for 30 seconds...
📊 Performance Results:
  Duration: 30.1s
  Total messages: 35
  Measurement data: 29
  Message rate: 1.2/sec
  Measurement rate: 1.0/sec
  Sequence gaps: 0
✅ Performance test PASSED

📋 Test Summary:
  Server Status: ✅ PASS
  WebSocket Connection: ✅ PASS
  Simulator Integration: ✅ PASS
  Performance: ✅ PASS

🎯 Overall Result: 4/4 tests passed
🎉 All tests PASSED! Phase 2.1 implementation is working correctly.
```

## 🔧 개발 가이드

### 서버 구조

```
main.py
├── PowerMonitoringServer    # 메인 서버 클래스
├── ConnectionManager        # WebSocket 연결 관리
└── FastAPI Routes          # REST API 엔드포인트
```

### 주요 컴포넌트

#### ConnectionManager
- WebSocket 클라이언트 연결 관리
- 메시지 브로드캐스팅
- 연결 상태 추적

#### PowerMonitoringServer
- 시뮬레이터 통합
- 데이터 수집 및 전송
- 비동기 태스크 관리

### 확장 포인트

Phase 2의 다음 단계들을 위한 확장 포인트:

1. **데이터베이스 연동** - SQLite 저장 로직 추가
2. **Chart.js 통합** - 실시간 그래프 구현
3. **통계 계산** - min/max/평균 계산 로직
4. **알림 시스템** - 임계값 기반 알림

## 🐛 문제 해결

### 서버 시작 실패
```bash
# 포트 사용 중인 경우
lsof -ti:8000 | xargs kill -9

# 의존성 문제
pip install --upgrade -r requirements.txt
```

### WebSocket 연결 실패
- 방화벽 설정 확인
- 브라우저 개발자 도구에서 네트워크 탭 확인
- 서버 로그 확인

### 데이터 수신 안됨
- 시뮬레이터 상태 확인: `GET /status`
- 시뮬레이터 재시작: `POST /simulator/start`

## 📈 성능 지표

### 목표 성능
- **데이터 레이트**: ≥ 0.8 samples/sec
- **WebSocket 지연**: < 100ms
- **연결 안정성**: 99%+
- **메모리 사용량**: < 50MB

### 실제 성능 (테스트 결과)
- **데이터 레이트**: 1.0 samples/sec ✅
- **메시지 레이트**: 1.2 messages/sec ✅
- **시퀀스 무결성**: 0 gaps ✅
- **연결 안정성**: 100% ✅

## 🔮 다음 단계 (Phase 2.2)

Phase 2.1 완료 후 다음 구현 예정:

1. **SQLite 데이터베이스 연동**
   - 실시간 데이터 저장
   - 48시간 데이터 관리
   - 히스토리 조회 API

2. **Chart.js 기반 그래프**
   - 실시간 라인 차트
   - 멀티축 W/V/A 표시
   - 60초 롤링 버퍼

3. **통계 패널**
   - 1분 min/max 계산
   - 이동평균 표시
   - 시각적 인디케이터

---

**Phase 2.1 Status**: ✅ **완료** - WebSocket 실시간 통신 구현 및 테스트 완료