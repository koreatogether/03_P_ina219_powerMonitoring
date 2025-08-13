#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INA219 Power Monitoring System - FastAPI Backend
Phase 3.1: SQLite Database Integration & Data Storage

기능:
- FastAPI 기본 서버
- WebSocket 엔드포인트  
- 시뮬레이터 연동
- 실시간 데이터 브로드캐스팅
- 1분 통계 패널
- 임계값 알림 시스템
- SQLite 데이터베이스 48시간 저장
- 히스토리 데이터 조회 API
- 자동 데이터 정리 시스템
"""

import os
import sys

# UTF-8 인코딩 강제 설정 (Windows 호환)
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
    os.environ['PYTHONIOENCODING'] = 'utf-8'

import asyncio
import json
import sys
import os
from typing import List
from datetime import datetime, timedelta

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

# 데이터베이스 모듈 임포트
from database import DatabaseManager, auto_cleanup_task

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
            description="Real-time power monitoring with WebSocket & Database",
            version="3.1.0"
        )
        self.manager = ConnectionManager()
        self.simulator = None
        self.is_running = False
        self.db = DatabaseManager.get_instance()
        
        # 1분 통계 버퍼
        self.minute_buffer = {
            'voltage': [],
            'current': [],
            'power': [],
            'start_time': None
        }
        
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
        
        .stats-panel {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .stats-metric {
            text-align: center;
            padding: 15px;
            border-radius: 8px;
            position: relative;
        }
        
        .stats-metric.voltage {
            background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
            color: white;
        }
        
        .stats-metric.current {
            background: linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%);
            color: white;
        }
        
        .stats-metric.power {
            background: linear-gradient(135deg, #ffe66d 0%, #ffcc02 100%);
            color: #333;
        }
        
        .stats-title {
            font-size: 14px;
            font-weight: bold;
            margin-bottom: 10px;
            opacity: 0.9;
        }
        
        .stats-values {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        
        .stats-value {
            text-align: center;
        }
        
        .stats-value-num {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 2px;
        }
        
        .stats-value-label {
            font-size: 10px;
            opacity: 0.8;
        }
        
        .alert-panel {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
        }
        
        .alert-item {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 8px;
        }
        
        .alert-item:last-child {
            margin-bottom: 0;
        }
        
        .alert-indicator {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: #28a745;
        }
        
        .alert-indicator.warning {
            background-color: #ffc107;
        }
        
        .alert-indicator.danger {
            background-color: #dc3545;
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
        
        #powerChart {
            background-color: white;
            border-radius: 5px;
        }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="header">
        <h1>🔋 INA219 Power Monitoring System</h1>
        <p>Phase 2.3: 1-Minute Statistics & Threshold Alerts</p>
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
        <h3>� Resal-time Chart</h3>
        <canvas id="powerChart" width="800" height="300"></canvas>
    </div>
    
    <div class="stats-panel">
        <h3>📊 1-Minute Statistics</h3>
        
        <div class="stats-grid">
            <div class="stats-metric voltage">
                <div class="stats-title">⚡ Voltage</div>
                <div class="stats-values">
                    <div class="stats-value">
                        <div class="stats-value-num" id="voltageMin">--</div>
                        <div class="stats-value-label">MIN (V)</div>
                    </div>
                    <div class="stats-value">
                        <div class="stats-value-num" id="voltageMax">--</div>
                        <div class="stats-value-label">MAX (V)</div>
                    </div>
                </div>
            </div>
            
            <div class="stats-metric current">
                <div class="stats-title">🔋 Current</div>
                <div class="stats-values">
                    <div class="stats-value">
                        <div class="stats-value-num" id="currentMin">--</div>
                        <div class="stats-value-label">MIN (A)</div>
                    </div>
                    <div class="stats-value">
                        <div class="stats-value-num" id="currentMax">--</div>
                        <div class="stats-value-label">MAX (A)</div>
                    </div>
                </div>
            </div>
            
            <div class="stats-metric power">
                <div class="stats-title">💡 Power</div>
                <div class="stats-values">
                    <div class="stats-value">
                        <div class="stats-value-num" id="powerMin">--</div>
                        <div class="stats-value-label">MIN (W)</div>
                    </div>
                    <div class="stats-value">
                        <div class="stats-value-num" id="powerMax">--</div>
                        <div class="stats-value-label">MAX (W)</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="alert-panel">
            <h4 style="margin: 0 0 10px 0;">🚨 Threshold Alerts</h4>
            <div class="alert-item">
                <div class="alert-indicator" id="voltageAlert"></div>
                <span id="voltageAlertText">Voltage: Normal (4.5V - 5.5V)</span>
            </div>
            <div class="alert-item">
                <div class="alert-indicator" id="currentAlert"></div>
                <span id="currentAlertText">Current: Normal (< 0.5A)</span>
            </div>
            <div class="alert-item">
                <div class="alert-indicator" id="powerAlert"></div>
                <span id="powerAlertText">Power: Normal (< 2.0W)</span>
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
        
        // 1분 통계 데이터
        let statsData = {
            voltage: [],
            current: [],
            power: [],
            startTime: null
        };
        
        // 임계값 설정
        const thresholds = {
            voltage: { min: 4.5, max: 5.5 },
            current: { max: 0.5 },
            power: { max: 2.0 }
        };
        
        // Chart.js 설정
        let powerChart = null;
        const maxDataPoints = 60; // 60초 버퍼
        const chartData = {
            labels: [],
            datasets: [
                {
                    label: 'Voltage (V)',
                    data: [],
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.1)',
                    yAxisID: 'y',
                    tension: 0.1
                },
                {
                    label: 'Current (A)',
                    data: [],
                    borderColor: 'rgb(54, 162, 235)',
                    backgroundColor: 'rgba(54, 162, 235, 0.1)',
                    yAxisID: 'y1',
                    tension: 0.1
                },
                {
                    label: 'Power (W)',
                    data: [],
                    borderColor: 'rgb(255, 205, 86)',
                    backgroundColor: 'rgba(255, 205, 86, 0.1)',
                    yAxisID: 'y1',
                    tension: 0.1
                }
            ]
        };
        
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
                        
                        // 실시간 수치 업데이트
                        document.getElementById('voltage').textContent = measurement.v.toFixed(3);
                        document.getElementById('current').textContent = measurement.a.toFixed(3);
                        document.getElementById('power').textContent = measurement.w.toFixed(3);
                        
                        // 차트에 데이터 추가
                        addDataToChart(measurement.v, measurement.a, measurement.w);
                        
                        // 통계 데이터 업데이트
                        updateStatistics(measurement.v, measurement.a, measurement.w);
                        
                        document.getElementById('lastData').innerHTML = 
                            `V=${measurement.v}V, A=${measurement.a}A, W=${measurement.w}W<br>` +
                            `Seq=${measurement.seq}, Mode=${measurement.mode}, Status=${measurement.status}`;
                        
                        // 파워 계산 검증
                        const calculatedPower = (measurement.v * measurement.a).toFixed(3);
                        log(`📊 Data: V=${measurement.v.toFixed(3)}V A=${measurement.a.toFixed(3)}A W=${measurement.w.toFixed(3)}W (calc: ${calculatedPower}W)`, 'info');
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
        
        function clearChart() {
            if (powerChart) {
                chartData.labels = [];
                chartData.datasets[0].data = [];
                chartData.datasets[1].data = [];
                chartData.datasets[2].data = [];
                powerChart.update();
                log('📈 Chart cleared', 'info');
            }
        }
        
        function clearLog() {
            document.getElementById('messageLog').innerHTML = '';
            clearChart();
            log('📋 Log and chart cleared', 'info');
        }
        
        function initChart() {
            const ctx = document.getElementById('powerChart').getContext('2d');
            powerChart = new Chart(ctx, {
                type: 'line',
                data: chartData,
                options: {
                    responsive: true,
                    interaction: {
                        mode: 'index',
                        intersect: false,
                    },
                    plugins: {
                        title: {
                            display: true,
                            text: 'Real-time Power Monitoring (Last 60 seconds)'
                        },
                        legend: {
                            display: true,
                            position: 'top'
                        }
                    },
                    scales: {
                        x: {
                            display: true,
                            title: {
                                display: true,
                                text: 'Time'
                            }
                        },
                        y: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                            title: {
                                display: true,
                                text: 'Voltage (V)',
                                color: 'rgb(255, 99, 132)'
                            },
                            grid: {
                                drawOnChartArea: false,
                            },
                            min: 0,
                            max: 6
                        },
                        y1: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            title: {
                                display: true,
                                text: 'Current (A) / Power (W)',
                                color: 'rgb(54, 162, 235)'
                            },
                            grid: {
                                drawOnChartArea: false,
                            },
                            min: 0,
                            max: 5
                        }
                    },
                    animation: {
                        duration: 200
                    }
                }
            });
        }
        
        function addDataToChart(voltage, current, power) {
            const now = new Date();
            const timeLabel = now.toLocaleTimeString();
            
            // 데이터 추가
            chartData.labels.push(timeLabel);
            chartData.datasets[0].data.push(voltage);
            chartData.datasets[1].data.push(current);
            chartData.datasets[2].data.push(power);
            
            // 60초 버퍼 유지 (오래된 데이터 제거)
            if (chartData.labels.length > maxDataPoints) {
                chartData.labels.shift();
                chartData.datasets[0].data.shift();
                chartData.datasets[1].data.shift();
                chartData.datasets[2].data.shift();
            }
            
            // 차트 업데이트
            if (powerChart) {
                powerChart.update('none'); // 애니메이션 없이 빠른 업데이트
            }
        }
        
        // 통계 데이터 업데이트 함수
        function updateStatistics(voltage, current, power) {
            const now = Date.now();
            
            // 1분 통계 시작 시간 설정
            if (!statsData.startTime) {
                statsData.startTime = now;
            }
            
            // 데이터 추가
            statsData.voltage.push(voltage);
            statsData.current.push(current);
            statsData.power.push(power);
            
            // 1분 이상된 데이터 제거
            const oneMinute = 60 * 1000;
            if (now - statsData.startTime > oneMinute) {
                statsData.voltage.shift();
                statsData.current.shift();
                statsData.power.shift();
            }
            
            // 통계 UI 업데이트
            updateStatsDisplay();
            
            // 임계값 알림 체크
            checkThresholds(voltage, current, power);
        }
        
        // 통계 디스플레이 업데이트
        function updateStatsDisplay() {
            if (statsData.voltage.length === 0) return;
            
            // Min/Max 계산
            const vMin = Math.min(...statsData.voltage);
            const vMax = Math.max(...statsData.voltage);
            const aMin = Math.min(...statsData.current);
            const aMax = Math.max(...statsData.current);
            const wMin = Math.min(...statsData.power);
            const wMax = Math.max(...statsData.power);
            
            // UI 업데이트
            document.getElementById('voltageMin').textContent = vMin.toFixed(3);
            document.getElementById('voltageMax').textContent = vMax.toFixed(3);
            document.getElementById('currentMin').textContent = aMin.toFixed(3);
            document.getElementById('currentMax').textContent = aMax.toFixed(3);
            document.getElementById('powerMin').textContent = wMin.toFixed(3);
            document.getElementById('powerMax').textContent = wMax.toFixed(3);
        }
        
        // 임계값 알림 체크
        function checkThresholds(voltage, current, power) {
            // 전압 체크
            const voltageAlert = document.getElementById('voltageAlert');
            const voltageText = document.getElementById('voltageAlertText');
            
            if (voltage < thresholds.voltage.min || voltage > thresholds.voltage.max) {
                voltageAlert.className = 'alert-indicator danger';
                voltageText.textContent = `Voltage: DANGER ${voltage.toFixed(3)}V (4.5V - 5.5V)`;
            } else if (voltage < thresholds.voltage.min + 0.2 || voltage > thresholds.voltage.max - 0.2) {
                voltageAlert.className = 'alert-indicator warning';
                voltageText.textContent = `Voltage: WARNING ${voltage.toFixed(3)}V (4.5V - 5.5V)`;
            } else {
                voltageAlert.className = 'alert-indicator';
                voltageText.textContent = `Voltage: Normal ${voltage.toFixed(3)}V (4.5V - 5.5V)`;
            }
            
            // 전류 체크
            const currentAlert = document.getElementById('currentAlert');
            const currentText = document.getElementById('currentAlertText');
            
            if (current > thresholds.current.max) {
                currentAlert.className = 'alert-indicator danger';
                currentText.textContent = `Current: OVERLOAD ${current.toFixed(3)}A (< 0.5A)`;
            } else if (current > thresholds.current.max - 0.1) {
                currentAlert.className = 'alert-indicator warning';
                currentText.textContent = `Current: WARNING ${current.toFixed(3)}A (< 0.5A)`;
            } else {
                currentAlert.className = 'alert-indicator';
                currentText.textContent = `Current: Normal ${current.toFixed(3)}A (< 0.5A)`;
            }
            
            // 전력 체크
            const powerAlert = document.getElementById('powerAlert');
            const powerText = document.getElementById('powerAlertText');
            
            if (power > thresholds.power.max) {
                powerAlert.className = 'alert-indicator danger';
                powerText.textContent = `Power: OVERLOAD ${power.toFixed(3)}W (< 2.0W)`;
            } else if (power > thresholds.power.max - 0.3) {
                powerAlert.className = 'alert-indicator warning';
                powerText.textContent = `Power: WARNING ${power.toFixed(3)}W (< 2.0W)`;
            } else {
                powerAlert.className = 'alert-indicator';
                powerText.textContent = `Power: Normal ${power.toFixed(3)}W (< 2.0W)`;
            }
        }
        
        window.onload = function() {
            log('🚀 WebSocket Dashboard Started', 'success');
            log('📈 Initializing real-time chart...', 'info');
            initChart();
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
            db_stats = await self.db.get_database_stats()
            return {
                "server": "running",
                "simulator": "connected" if self.simulator and self.simulator.is_connected() else "disconnected",
                "websocket_connections": len(self.manager.active_connections),
                "database": db_stats,
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
        
        # 새로운 데이터베이스 API 엔드포인트들
        @self.app.get("/api/measurements")
        async def get_measurements(hours: int = 24, limit: int = 1000):
            """측정 데이터 조회"""
            try:
                measurements = await self.db.get_recent_measurements(hours=hours, limit=limit)
                return {
                    "data": measurements,
                    "count": len(measurements),
                    "hours": hours,
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/statistics")
        async def get_statistics(hours: int = 24):
            """1분 통계 데이터 조회"""
            try:
                statistics = await self.db.get_minute_statistics(hours=hours)
                return {
                    "data": statistics,
                    "count": len(statistics),
                    "hours": hours,
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/alerts")
        async def get_alerts(hours: int = 24, severity: str = None):
            """알림 이벤트 조회"""
            try:
                alerts = await self.db.get_alert_events(hours=hours, severity=severity)
                return {
                    "data": alerts,
                    "count": len(alerts),
                    "hours": hours,
                    "severity_filter": severity,
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/logs")
        async def get_logs(hours: int = 24, level: str = None, component: str = None):
            """시스템 로그 조회"""
            try:
                logs = await self.db.get_system_logs(hours=hours, level=level, component=component)
                return {
                    "data": logs,
                    "count": len(logs),
                    "hours": hours,
                    "level_filter": level,
                    "component_filter": component,
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/power-efficiency")
        async def get_power_efficiency(hours: int = 24):
            """전력 효율성 분석"""
            try:
                efficiency = await self.db.calculate_power_efficiency(hours=hours)
                return {
                    "data": efficiency,
                    "hours": hours,
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/database/cleanup")
        async def cleanup_database():
            """데이터베이스 정리"""
            try:
                cleanup_stats = await self.db.cleanup_old_data()
                return {
                    "status": "completed",
                    "stats": cleanup_stats,
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/database/vacuum")
        async def vacuum_database():
            """데이터베이스 최적화"""
            try:
                success = await self.db.vacuum_database()
                return {
                    "status": "completed" if success else "failed",
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/database/stats")
        async def get_database_stats():
            """데이터베이스 통계"""
            try:
                stats = await self.db.get_database_stats()
                return {
                    "data": stats,
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
    
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
                                voltage = json_data['v']
                                current = json_data['a']
                                power = json_data['w']
                                
                                # 데이터베이스에 저장
                                await self.db.save_measurement(
                                    voltage=voltage,
                                    current=current,
                                    power=power,
                                    sequence_number=json_data.get('seq'),
                                    sensor_status=json_data.get('status', 'ok'),
                                    simulation_mode=json_data.get('mode', 'NORMAL')
                                )
                                
                                # 1분 통계 버퍼 업데이트
                                await self.update_minute_statistics(voltage, current, power)
                                
                                # 임계값 알림 체크
                                await self.check_and_save_alerts(voltage, current, power)
                                
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
    
    async def update_minute_statistics(self, voltage: float, current: float, power: float):
        """1분 통계 버퍼 업데이트"""
        try:
            now = datetime.now()
            
            # 1분 버퍼 시작 시간 설정
            if not self.minute_buffer['start_time']:
                self.minute_buffer['start_time'] = now
            
            # 1분이 지났으면 통계 저장하고 버퍼 리셋
            if (now - self.minute_buffer['start_time']).total_seconds() >= 60:
                if self.minute_buffer['voltage']:
                    # 통계 계산
                    voltage_stats = {
                        'min': min(self.minute_buffer['voltage']),
                        'max': max(self.minute_buffer['voltage']),
                        'avg': sum(self.minute_buffer['voltage']) / len(self.minute_buffer['voltage'])
                    }
                    current_stats = {
                        'min': min(self.minute_buffer['current']),
                        'max': max(self.minute_buffer['current']),
                        'avg': sum(self.minute_buffer['current']) / len(self.minute_buffer['current'])
                    }
                    power_stats = {
                        'min': min(self.minute_buffer['power']),
                        'max': max(self.minute_buffer['power']),
                        'avg': sum(self.minute_buffer['power']) / len(self.minute_buffer['power'])
                    }
                    
                    # 데이터베이스에 저장
                    minute_timestamp = self.minute_buffer['start_time'].replace(second=0, microsecond=0)
                    await self.db.save_minute_statistics(
                        minute_timestamp=minute_timestamp,
                        voltage_stats=voltage_stats,
                        current_stats=current_stats,
                        power_stats=power_stats,
                        sample_count=len(self.minute_buffer['voltage'])
                    )
                
                # 버퍼 리셋
                self.minute_buffer = {
                    'voltage': [],
                    'current': [],
                    'power': [],
                    'start_time': now
                }
            
            # 현재 데이터를 버퍼에 추가
            self.minute_buffer['voltage'].append(voltage)
            self.minute_buffer['current'].append(current)
            self.minute_buffer['power'].append(power)
            
        except Exception as e:
            print(f"❌ Failed to update minute statistics: {e}")
    
    async def check_and_save_alerts(self, voltage: float, current: float, power: float):
        """임계값 알림 체크 및 저장"""
        try:
            # 임계값 설정
            thresholds = {
                'voltage': {'min': 4.5, 'max': 5.5, 'warning_range': 0.2},
                'current': {'max': 0.5, 'warning_range': 0.1},
                'power': {'max': 2.0, 'warning_range': 0.3}
            }
            
            # 전압 체크
            if voltage < thresholds['voltage']['min'] or voltage > thresholds['voltage']['max']:
                await self.db.save_alert_event(
                    alert_type="threshold_violation",
                    metric_name="voltage",
                    metric_value=voltage,
                    threshold_value=thresholds['voltage']['min'] if voltage < thresholds['voltage']['min'] else thresholds['voltage']['max'],
                    severity="danger",
                    message=f"Voltage out of range: {voltage:.3f}V (safe: 4.5V-5.5V)"
                )
            elif (voltage < thresholds['voltage']['min'] + thresholds['voltage']['warning_range'] or 
                  voltage > thresholds['voltage']['max'] - thresholds['voltage']['warning_range']):
                await self.db.save_alert_event(
                    alert_type="threshold_warning",
                    metric_name="voltage",
                    metric_value=voltage,
                    threshold_value=thresholds['voltage']['min'] + thresholds['voltage']['warning_range'],
                    severity="warning",
                    message=f"Voltage near limit: {voltage:.3f}V (safe: 4.5V-5.5V)"
                )
            
            # 전류 체크
            if current > thresholds['current']['max']:
                await self.db.save_alert_event(
                    alert_type="threshold_violation",
                    metric_name="current",
                    metric_value=current,
                    threshold_value=thresholds['current']['max'],
                    severity="danger",
                    message=f"Current overload: {current:.3f}A (max: 0.5A)"
                )
            elif current > thresholds['current']['max'] - thresholds['current']['warning_range']:
                await self.db.save_alert_event(
                    alert_type="threshold_warning",
                    metric_name="current",
                    metric_value=current,
                    threshold_value=thresholds['current']['max'] - thresholds['current']['warning_range'],
                    severity="warning",
                    message=f"Current near limit: {current:.3f}A (max: 0.5A)"
                )
            
            # 전력 체크
            if power > thresholds['power']['max']:
                await self.db.save_alert_event(
                    alert_type="threshold_violation",
                    metric_name="power",
                    metric_value=power,
                    threshold_value=thresholds['power']['max'],
                    severity="danger",
                    message=f"Power overload: {power:.3f}W (max: 2.0W)"
                )
            elif power > thresholds['power']['max'] - thresholds['power']['warning_range']:
                await self.db.save_alert_event(
                    alert_type="threshold_warning",
                    metric_name="power",
                    metric_value=power,
                    threshold_value=thresholds['power']['max'] - thresholds['power']['warning_range'],
                    severity="warning",
                    message=f"Power near limit: {power:.3f}W (max: 2.0W)"
                )
                
        except Exception as e:
            print(f"❌ Failed to check alerts: {e}")
    
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
    print("🗄️ Database: SQLite with 48-hour retention")
    
    # 데이터베이스 시스템 로그 저장
    await server.db.save_system_log(
        level="INFO",
        component="server",
        message="Server startup initiated",
        details={"version": "3.1.0", "phase": "Phase 3.1 - Database Integration"}
    )
    
    # 데이터 수집 시작
    await server.start_data_collection()
    
    # 자동 정리 태스크 시작
    asyncio.create_task(auto_cleanup_task())
    print("🔄 Auto cleanup task started")


@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 이벤트"""
    print("🛑 INA219 Power Monitoring Server Shutting down...")
    
    # 종료 로그 저장
    await server.db.save_system_log(
        level="INFO",
        component="server",
        message="Server shutdown initiated"
    )
    
    await server.stop_data_collection()


def main():
    """메인 함수"""
    print("=" * 60)
    print("🔋 INA219 Power Monitoring System")
    print("🗄️ Phase 3.1: SQLite Database Integration & Data Storage")
    print("=" * 60)
    
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