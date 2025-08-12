# INA219 전력 모니터링 시스템 2차 아키텍처 설계

## 1. 시스템 개요

기존 여러 AI 모델의 설계안과 사용자 요구사항을 통합하여, 실용적이고 확장 가능한 INA219 전력 모니터링 시스템을 설계합니다. 아두이노 MOCK 시뮬레이터를 포함하여 개발 효율성을 극대화합니다.

## 2. 핵심 요구사항 통합

### 2.1 사용자 명시 요구사항 (02_human_architecture.md 기반)
- ✅ 아두이노 MOCK 시뮬레이터 제공 (개발환경 독립성)
- ✅ 시리얼 통신 기반 JSON 포맷 송수신
- ✅ 데이터 무결성 체크, 재전송, ACK/NACK
- ✅ 로컬서버 형태 대시보드
- ✅ 실시간 W/V/A 값 표시 (숫자 + 선 그래프)
- ✅ 지난 1분간 min/max 값 표시
- ✅ 별도 스레드로 시리얼 데이터 처리
- ✅ 데이터 분석 그래프 (이동평균, min/max)
- ✅ 48시간 기록 로그 저장

### 2.2 기존 설계안 장점 통합
- **FastAPI + WebSocket**: 실시간성과 확장성 (01_claudeCode)
- **Python Dash**: 빠른 프로토타이핑과 시각화 (01_gpt4-1, 01_microsoft, 01_solarPro2)
- **멀티축 그래프**: 서로 다른 스케일의 W/V/A 동시 표시 (01_solarPro2)
- **스레드 분리**: UI 블로킹 방지 (공통)

## 3. 최종 시스템 아키텍처

```
Arduino/Mock Simulator → Serial/JSON → Python Backend → WebSocket → Dashboard
                                     ↓
                                  SQLite DB (48h 로그)
```

### 3.1 아두이노 계층 & MOCK 시뮬레이터
**아두이노 부분**:
- 기존 INA219 측정 로직 유지
- JSON 포맷으로 시리얼 전송: `{"v": 5.02, "a": 0.245, "w": 1.23, "ts": 1712345678, "seq": 123}`
- 명령 수신 처리: 측정 주기 변경, 임계값 설정 등

**MOCK 시뮬레이터 (신규)**:
- 실제 하드웨어 없이도 개발 가능
- 랜덤/패턴 데이터 생성으로 다양한 시나리오 테스트
- 동일한 JSON 포맷으로 시리얼 에뮬레이션
- 구현 위치: `src/python/simulator/arduino_mock.py`

### 3.2 Python Backend (확장된 설계)

**핵심 컴포넌트**:

```python
# 데이터 수집 계층
├── SerialReader         # 시리얼 포트 관리 + JSON 파싱
├── DataValidator        # 데이터 무결성 검증 + 시퀀스 체크
├── DatabaseManager      # SQLite 48시간 로그 저장
└── MockController       # 아두이노 시뮬레이터 제어

# 실시간 서비스 계층  
├── WebSocketServer      # 대시보드 실시간 통신
├── DataProcessor        # 이동평균, min/max 계산
└── AlertManager         # 임계값 기반 알림 처리

# API 계층
└── FastAPI             # REST API + WebSocket 엔드포인트
```

**기술 스택**:
- **FastAPI**: WebSocket + REST API 통합
- **SQLite**: 경량화된 48시간 데이터 저장
- **pySerial**: 시리얼 통신 + Mock 지원
- **asyncio**: 비동기 처리로 성능 최적화

### 3.3 Dashboard 계층 (하이브리드 설계)

**기본 구조**: FastAPI + WebSocket + Vanilla JavaScript
- **실시간 업데이트**: WebSocket으로 100ms 간격 데이터 수신
- **그래프 라이브러리**: Chart.js (경량화, 실시간 성능 우수)
- **반응형 UI**: Bootstrap 기반 모바일 지원

**주요 화면 구성**:
```
┌─────────────────────────────────────────┐
│  실시간 수치 (W/V/A) + 상태 인디케이터    │
├─────────────────────────────────────────┤
│  멀티축 실시간 그래프 (60초 버퍼)        │
├─────────────────────────────────────────┤
│  1분 min/max + 이동평균 통계 패널       │
├─────────────────────────────────────────┤
│  48시간 히스토리 그래프 (선택적)         │
└─────────────────────────────────────────┘
```

## 4. 데이터 플로우 및 통신 프로토콜

### 4.1 정방향 데이터 플로우
```json
// Arduino/Mock → Python (1초 주기)
{
  "v": 5.02,           // 전압 (V)
  "a": 0.245,          // 전류 (A)  
  "w": 1.23,           // 전력 (W)
  "ts": 1712345678,    // 타임스탬프
  "seq": 123,          // 시퀀스 번호 (무결성 체크)
  "status": "ok"       // 센서 상태
}
```

### 4.2 역방향 제어 플로우
```json
// Python → Arduino (필요시)
{
  "cmd": "set_interval",
  "value": 500,        // 측정 주기 (ms)
  "seq": 124
}

// Arduino → Python (ACK/NACK)
{
  "ack": 124,
  "result": "ok"
}
```

### 4.3 WebSocket 프로토콜 (Dashboard ↔ Backend)
```json
// Backend → Dashboard (실시간 데이터)
{
  "type": "realtime",
  "data": {
    "current": {"v": 5.02, "a": 0.245, "w": 1.23},
    "stats": {
      "min_1m": {"v": 4.98, "a": 0.200, "w": 1.10},
      "max_1m": {"v": 5.15, "a": 0.280, "w": 1.35},
      "avg_1m": {"v": 5.05, "a": 0.242, "w": 1.25}
    }
  }
}
```

## 5. 데이터 저장 및 분석 설계

### 5.1 SQLite 테이블 구조
```sql
CREATE TABLE power_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,
    voltage REAL NOT NULL,
    current REAL NOT NULL, 
    power REAL NOT NULL,
    sequence INTEGER,
    status TEXT DEFAULT 'ok',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_timestamp ON power_log(timestamp);
```

### 5.2 48시간 데이터 관리
- **자동 정리**: 48시간 이전 데이터 주기적 삭제
- **압축 저장**: 분 단위 평균값으로 장기 보관 옵션
- **백업**: 일 단위 CSV 익스포트 기능

### 5.3 실시간 분석 기능
```python
# 이동평균 (1분, 5분, 15분)
moving_avg_1m = data.rolling(window=60).mean()

# 이상치 탐지 (Z-score 기반)
z_scores = np.abs(stats.zscore(data))
outliers = data[z_scores > 3]

# min/max/평균 통계
stats_1m = {
    'min': data.tail(60).min(),
    'max': data.tail(60).max(), 
    'avg': data.tail(60).mean()
}
```

## 6. 디렉토리 구조 (최종)

```
src/
├── arduino/
│   └── main.ino                    # 기존 아두이노 코드
├── python/
│   ├── backend/
│   │   ├── main.py                 # FastAPI 메인 서버
│   │   ├── serial_manager.py       # 시리얼 통신 + Mock 지원
│   │   ├── data_processor.py       # 데이터 분석 + 통계
│   │   ├── database.py             # SQLite 관리
│   │   └── websocket_handler.py    # WebSocket 엔드포인트
│   ├── simulator/
│   │   └── arduino_mock.py         # 아두이노 MOCK 시뮬레이터
│   └── dashboard/
│       ├── static/
│       │   ├── js/
│       │   │   ├── dashboard.js    # 실시간 대시보드 로직
│       │   │   └── charts.js       # Chart.js 설정
│       │   ├── css/
│       │   │   └── style.css       # 대시보드 스타일
│       │   └── lib/                # Chart.js, Bootstrap CDN
│       └── templates/
│           └── index.html          # 메인 대시보드 페이지
├── data/
│   ├── logs/                       # SQLite DB 파일
│   └── exports/                    # CSV 백업 파일
└── docs/
    └── architecture/               # 설계 문서
```

## 7. 구현 우선순위 및 단계별 계획

### Phase 1: 기본 인프라 (1-2주)
1. ✅ MOCK 시뮬레이터 구현
2. ✅ 시리얼 통신 + JSON 파싱
3. ✅ SQLite 데이터베이스 설계
4. ✅ 기본 FastAPI 서버 구축

### Phase 2: 실시간 대시보드 (1주) 
1. ✅ WebSocket 실시간 통신
2. ✅ Chart.js 기반 그래프 구현
3. ✅ 멀티축 W/V/A 표시
4. ✅ 1분 min/max 통계 패널

### Phase 3: 고급 기능 (1주)
1. ✅ 이동평균 + 이상치 탐지
2. ✅ 48시간 히스토리 그래프
3. ✅ 데이터 무결성 체크 + 재전송
4. ✅ 임계값 알림 시스템

### Phase 4: 최적화 및 배포 (1주)
1. ✅ 성능 최적화 + 메모리 관리
2. ✅ 에러 핸들링 강화
3. ✅ Docker 컨테이너화
4. ✅ 문서화 완료

## 8. 예상 기술적 이점

### 8.1 개발 효율성
- **MOCK 시뮬레이터**: 하드웨어 의존성 제거, 병렬 개발 가능
- **FastAPI 자동 문서화**: API 명세 자동 생성
- **Hot Reload**: 개발 중 실시간 변경 반영

### 8.2 운영 안정성  
- **데이터 무결성**: 시퀀스 체크 + 재전송 메커니즘
- **에러 복구**: 연결 끊김 시 자동 재연결
- **로그 관리**: 48시간 순환 저장으로 디스크 공간 최적화

### 8.3 확장성
- **멀티 디바이스**: 여러 아두이노 동시 모니터링 가능
- **클라우드 연동**: REST API로 외부 시스템 연동 용이
- **플러그인**: 새로운 센서/기능 추가 용이한 모듈 구조

## 9. 결론

본 설계는 기존 여러 AI 모델의 장점을 통합하되, 사용자가 명시한 핵심 요구사항(MOCK 시뮬레이터, 48시간 로그, 데이터 분석)을 충실히 반영했습니다. 특히 개발 효율성과 운영 안정성을 동시에 확보할 수 있는 실용적인 아키텍처로 설계되었습니다.

**핵심 차별점**:
- 🔧 **아두이노 MOCK 시뮬레이터**로 개발 생산성 극대화
- 📊 **FastAPI + WebSocket + Chart.js** 조합으로 최적의 실시간 성능
- 🗄️ **SQLite 기반 48시간 로그**로 경량화된 데이터 관리
- 🔄 **데이터 무결성 보장**으로 산업용 수준 안정성 확보