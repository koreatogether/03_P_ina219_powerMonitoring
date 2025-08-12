#!/usr/bin/env python3
"""
INA219 Power Monitoring System - FastAPI Backend
Phase 2.1: WebSocket 실시간 통신 최소 구현

기능:
- FastAPI 기본 서버
- WebSocket 엔드포인트
- 시뮬레이터 연동
- 실시간 데이터 브로드캐스팅
"""

import asyncio
import json
import sys
import os
from typing import List
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

# 시뮬레이터 패키지 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from simulator import create_simulator
except ImportError:
    print("❌ Simulator package not found. Please check the path.")
    sys.exit(1)


class ConnectionManager:
    """WebSocket 연결 관리자"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """클라이언트 연결"""
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"✅ Client connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """클라이언트 연결 해제"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"🔌 Client disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: str):
        """모든 연결된 클라이언트에게 메시지 브로드캐스트"""
        if not self.active_connections:
            return
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"❌ Failed to send message to client: {e}")
                disconnected.append(connection)
        
        # 연결이 끊어진 클라이언트 제거
        for connection in disconnected:
            self.disconnect(connection)


class PowerMonitoringServer:
    """전력 모니터링 서버"""
    
    def __init__(self):
        self.app = FastAPI(
            title="INA219 Power Monitoring System",
            description="Real-time power monitoring with WebSocket",
            version="1.0.0"
        )
        self.manager = ConnectionManager()
        self.simulator = None
        self.is_running = False
        
        # 라우트 설정
        self.setup_routes()
    
    def setup_routes(self):
        """API 라우트 설정"""
        
        @self.app.get("/")
        async def root():
            """루트 페이지 - 실시간 대시보드"""
            html_content = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>INA219 WebSocket Dashboard</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
        
        .container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .panel {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .status {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 15px;
        }
        
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background-color: #dc3545;
        }
        
        .status-indicator.connected {
            background-color: #28a745;
        }
        
        .controls {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        
        button {
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s;
        }
        
        .btn-primary {
            background-color: #007bff;
            color: white;
        }
        
        .btn-primary:hover {
            background-color: #0056b3;
        }
        
        .btn-danger {
            background-color: #dc3545;
            color: white;
        }
        
        .btn-danger:hover {
            background-color: #c82333;
        }
        
        .btn-success {
            background-color: #28a745;
            color: white;
        }
        
        .btn-success:hover {
            background-color: #218838;
        }
        
        .measurement {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-bottom: 15px;
        }
        
        .metric {
            text-align: center;
            padding: 15px;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            border-radius: 8px;
        }
        
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .metric-label {
            font-size: 12px;
            opacity: 0.9;
        }
        
        .data-display {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 15px;
            font-family: 'Courier New', monospace;
        }
        
        .log {
            height: 300px;
            overflow-y: auto;
            background-color: #000;
            color: #00ff00;
            padding: 10px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            margin-top: 15px;
        }
        
        .stat-item {
            text-align: center;
            padding: 10px;
            background-color: #e9ecef;
            border-radius: 5px;
        }
        
        .stat-value {
            font-size: 18px;
            font-weight: bold;
            color: #495057;
        }
        
        .stat-label {
            font-size: 11px;
            color: #6c757d;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔋 INA219 Power Monitoring System</h1>
        <p>Phase 2.1: WebSocket Real-time Communication</p>
    </div>
    
    <div class="container">
        <div class="panel">
            <h3>📡 Connection Control</h3>
            
            <div class="status">
                <div class="status-indicator" id="wsStatus"></div>
                <span id="wsStatusText">Disconnected</span>
            </div>
            
            <div class="controls">
                <button class="btn-primary" onclick="connectWebSocket()">Connect</button>
                <button class="btn-danger" onclick="disconnectWebSocket()">Disconnect</button>
                <button class="btn-success" onclick="clearLog()">Clear Log</button>
            </div>
            
            <div class="stats">
                <div class="stat-item">
                    <div class="stat-value" id="messageCount">0</div>
                    <div class="stat-label">Messages</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="dataRate">0.0</div>
                    <div class="stat-label">Rate/sec</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="uptime">00:00</div>
                    <div class="stat-label">Uptime</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="errorCount">0</div>
                    <div class="stat-label">Errors</div>
                </div>
            </div>
        </div>
        
        <div class="panel">
            <h3>⚡ Real-time Data</h3>
            
            <div class="measurement">
                <div class="metric">
                    <div class="metric-value" id="voltage">--</div>
                    <div class="metric-label">Voltage (V)</div>
                </div>
                <div class="metric">
                    <div class="metric-value" id="current">--</div>
                    <div class="metric-label">Current (A)</div>
                </div>
                <div class="metric">
                    <div class="metric-value" id="power">--</div>
                    <div class="metric-label">Power (W)</div>
                </div>
            </div>
            
            <div class="data-display">
                <strong>Last Data:</strong><br>
                <span id="lastData">No data received</span>
            </div>
        </div>
    </div>
    
    <div class="panel">
        <h3>📋 Message Log</h3>
        <div class="log" id="messageLog"></div>
    </div>

    <script>
        let ws = null;
        let messageCount = 0;
        let errorCount = 0;
        let startTime = null;
        let lastMessageTime = 0;
        let messageRate = 0;
        
        function log(message, type = 'info') {
            const logElement = document.getElementById('messageLog');
            const timestamp = new Date().toLocaleTimeString();
            const color = type === 'error' ? '#ff6b6b' : type === 'success' ? '#51cf66' : '#00ff00';
            
            logElement.innerHTML += `<span style="color: ${color}">[${timestamp}] ${message}</span>\\n`;
            logElement.scrollTop = logElement.scrollHeight;
        }
        
        function updateStats() {
            document.getElementById('messageCount').textContent = messageCount;
            document.getElementById('errorCount').textContent = errorCount;
            
            if (startTime) {
                const uptime = Math.floor((Date.now() - startTime) / 1000);
                const minutes = Math.floor(uptime / 60);
                const seconds = uptime % 60;
                document.getElementById('uptime').textContent = 
                    `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            }
            
            const now = Date.now();
            if (lastMessageTime > 0) {
                const timeDiff = (now - lastMessageTime) / 1000;
                if (timeDiff > 0) {
                    messageRate = 1 / timeDiff;
                }
            }
            document.getElementById('dataRate').textContent = messageRate.toFixed(1);
            lastMessageTime = now;
        }
        
        function connectWebSocket() {
            if (ws && ws.readyState === WebSocket.OPEN) {
                log('Already connected', 'info');
                return;
            }
            
            const wsUrl = `ws://${window.location.host}/ws`;
            log(`Connecting to ${wsUrl}...`, 'info');
            
            ws = new WebSocket(wsUrl);
            
            ws.onopen = function(event) {
                log('✅ WebSocket connected successfully', 'success');
                document.getElementById('wsStatus').classList.add('connected');
                document.getElementById('wsStatusText').textContent = 'Connected';
                startTime = Date.now();
                messageCount = 0;
                errorCount = 0;
            };
            
            ws.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);
                    messageCount++;
                    
                    if (data.type === 'measurement') {
                        const measurement = data.data;
                        document.getElementById('voltage').textContent = measurement.v.toFixed(3);
                        document.getElementById('current').textContent = measurement.a.toFixed(3);
                        document.getElementById('power').textContent = measurement.w.toFixed(3);
                        
                        document.getElementById('lastData').innerHTML = 
                            `V=${measurement.v}V, A=${measurement.a}A, W=${measurement.w}W<br>` +
                            `Seq=${measurement.seq}, Mode=${measurement.mode}, Status=${measurement.status}`;
                        
                        log(`📊 Data: V=${measurement.v.toFixed(3)}V A=${measurement.a.toFixed(3)}A W=${measurement.w.toFixed(3)}W`, 'info');
                    } else if (data.type === 'status') {
                        log(`📢 Status: ${data.message}`, 'info');
                    } else {
                        log(`📨 Message: ${JSON.stringify(data)}`, 'info');
                    }
                    
                    updateStats();
                } catch (e) {
                    errorCount++;
                    log(`❌ Parse error: ${e.message}`, 'error');
                    updateStats();
                }
            };
            
            ws.onclose = function(event) {
                log(`🔌 WebSocket closed (code: ${event.code})`, 'info');
                document.getElementById('wsStatus').classList.remove('connected');
                document.getElementById('wsStatusText').textContent = 'Disconnected';
            };
            
            ws.onerror = function(error) {
                errorCount++;
                log(`❌ WebSocket error: ${error}`, 'error');
                updateStats();
            };
        }
        
        function disconnectWebSocket() {
            if (ws) {
                ws.close();
                ws = null;
                log('🔌 WebSocket disconnected by user', 'info');
            }
        }
        
        function clearLog() {
            document.getElementById('messageLog').innerHTML = '';
            log('📋 Log cleared', 'info');
        }
        
        window.onload = function() {
            log('🚀 WebSocket Dashboard Started', 'success');
            log('Click "Connect" to start receiving real-time data', 'info');
        };
        
        window.onbeforeunload = function() {
            if (ws) {
                ws.close();
            }
        };
        
        setInterval(updateStats, 1000);
    </script>
</body>
</html>
            """
            return HTMLResponse(content=html_content)
        
        @self.app.get("/status")
        async def status():
            """시스템 상태"""
            return {
                "server": "running",
                "simulator": "connected" if self.simulator and self.simulator.is_connected() else "disconnected",
                "websocket_connections": len(self.manager.active_connections),
                "timestamp": datetime.now().isoformat()
            }
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket 엔드포인트"""
            await self.manager.connect(websocket)
            try:
                while True:
                    # 클라이언트로부터 메시지 수신 (keep-alive)
                    try:
                        data = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                        print(f"📨 Received from client: {data}")
                    except asyncio.TimeoutError:
                        pass  # 타임아웃은 정상 (keep-alive)
                    except Exception as e:
                        print(f"❌ WebSocket receive error: {e}")
                        break
            except WebSocketDisconnect:
                self.manager.disconnect(websocket)
        
        @self.app.post("/simulator/start")
        async def start_simulator():
            """시뮬레이터 시작"""
            if self.simulator and self.simulator.is_connected():
                return {"status": "already_running"}
            
            try:
                self.simulator = create_simulator("MOCK")
                if self.simulator.connect():
                    return {"status": "started", "type": self.simulator.get_simulator_type()}
                else:
                    return {"status": "failed", "error": "Connection failed"}
            except Exception as e:
                return {"status": "error", "error": str(e)}
        
        @self.app.post("/simulator/stop")
        async def stop_simulator():
            """시뮬레이터 중지"""
            if self.simulator:
                self.simulator.disconnect()
                self.simulator = None
                return {"status": "stopped"}
            return {"status": "not_running"}
    
    async def data_collector(self):
        """시뮬레이터에서 데이터 수집 및 브로드캐스트"""
        print("🔄 Data collector started")
        
        while self.is_running:
            if self.simulator and self.simulator.is_connected():
                try:
                    # 시뮬레이터에서 데이터 읽기
                    data = self.simulator.read_data(timeout=0.1)
                    
                    if data:
                        try:
                            # JSON 파싱
                            json_data = json.loads(data)
                            
                            # 측정 데이터인지 확인
                            if 'v' in json_data and 'a' in json_data and 'w' in json_data:
                                # WebSocket으로 브로드캐스트
                                websocket_message = {
                                    "type": "measurement",
                                    "data": json_data,
                                    "timestamp": datetime.now().isoformat()
                                }
                                
                                await self.manager.broadcast(json.dumps(websocket_message))
                            
                            elif json_data.get("type") == "status":
                                # 상태 메시지 브로드캐스트
                                websocket_message = {
                                    "type": "status",
                                    "message": json_data.get("message", ""),
                                    "timestamp": datetime.now().isoformat()
                                }
                                
                                await self.manager.broadcast(json.dumps(websocket_message))
                        
                        except json.JSONDecodeError:
                            # JSON이 아닌 데이터는 무시
                            pass
                
                except Exception as e:
                    print(f"❌ Data collection error: {e}")
            
            # 100ms 대기 (10Hz 업데이트)
            await asyncio.sleep(0.1)
        
        print("🛑 Data collector stopped")
    
    async def start_data_collection(self):
        """데이터 수집 시작"""
        if not self.is_running:
            self.is_running = True
            
            # 시뮬레이터 자동 시작
            if not self.simulator:
                self.simulator = create_simulator("MOCK")
                if self.simulator.connect():
                    print(f"✅ Simulator connected: {self.simulator.get_simulator_type()}")
                else:
                    print("❌ Failed to connect simulator")
            
            # 데이터 수집 태스크 시작
            asyncio.create_task(self.data_collector())
    
    async def stop_data_collection(self):
        """데이터 수집 중지"""
        self.is_running = False
        if self.simulator:
            self.simulator.disconnect()
            self.simulator = None


# 전역 서버 인스턴스
server = PowerMonitoringServer()
app = server.app


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 이벤트"""
    print("🚀 INA219 Power Monitoring Server Starting...")
    print("📡 WebSocket endpoint: ws://localhost:8000/ws")
    print("🌐 API docs: http://localhost:8000/docs")
    
    # 데이터 수집 시작
    await server.start_data_collection()


@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 이벤트"""
    print("🛑 INA219 Power Monitoring Server Shutting down...")
    await server.stop_data_collection()


def main():
    """메인 함수"""
    print("=" * 50)
    print("🔋 INA219 Power Monitoring System")
    print("📡 Phase 2.1: WebSocket Real-time Communication")
    print("=" * 50)
    
    # 서버 실행
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()