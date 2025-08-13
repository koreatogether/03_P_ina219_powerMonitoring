#!/usr/bin/env python3
"""
INA219 Power Monitoring System - Dash Dashboard
실시간 전력 모니터링 웹 대시보드
"""

import queue
import threading
import time
from datetime import datetime

import dash
import pandas as pd
import plotly.graph_objs as go
import serial
from dash import Input, Output, State, dcc, html


class PowerMonitoringDashboard:
    def __init__(self):
        self.app = dash.Dash(__name__)
        self.data_queue = queue.Queue()
        self.data_buffer = pd.DataFrame(
            columns=["timestamp", "voltage", "current", "power"]
        )
        self.max_buffer_size = 1000
        self.serial_port = None
        self.is_collecting = False

        # 대시보드 레이아웃 설정
        self.setup_layout()
        self.setup_callbacks()

    def setup_layout(self):
        """대시보드 레이아웃 구성"""
        self.app.layout = html.Div(
            [
                # 헤더
                html.Div(
                    [
                        html.H1(
                            "INA219 Power Monitoring System", className="header-title"
                        ),
                        html.P(
                            "실시간 전력 모니터링 대시보드", className="header-subtitle"
                        ),
                    ],
                    className="header",
                ),
                # 연결 설정 패널
                html.Div(
                    [
                        html.H3("연결 설정"),
                        html.Div(
                            [
                                html.Label("시리얼 포트:"),
                                dcc.Input(
                                    id="serial-port-input",
                                    type="text",
                                    value="COM3",  # Windows 기본값
                                    placeholder="예: COM3 (Windows) 또는 /dev/ttyUSB0 (Linux)",
                                ),
                                html.Button("연결", id="connect-btn", n_clicks=0),
                                html.Button(
                                    "연결 해제", id="disconnect-btn", n_clicks=0
                                ),
                                html.Div(
                                    id="connection-status", className="status-indicator"
                                ),
                            ],
                            className="connection-panel",
                        ),
                    ],
                    className="control-panel",
                ),
                # 실시간 데이터 표시
                html.Div(
                    [
                        html.Div(
                            [
                                html.H4("현재 측정값"),
                                html.Div(
                                    id="current-values", className="current-values"
                                ),
                            ],
                            className="current-data-panel",
                        )
                    ]
                ),
                # 그래프 영역
                html.Div(
                    [
                        # 전압 그래프
                        html.Div(
                            [dcc.Graph(id="voltage-graph")], className="graph-container"
                        ),
                        # 전류 그래프
                        html.Div(
                            [dcc.Graph(id="current-graph")], className="graph-container"
                        ),
                        # 전력 그래프
                        html.Div(
                            [dcc.Graph(id="power-graph")], className="graph-container"
                        ),
                    ],
                    className="graphs-container",
                ),
                # 통계 정보
                html.Div(
                    [html.H3("통계 정보"), html.Div(id="statistics-panel")],
                    className="statistics-container",
                ),
                # 자동 업데이트 컴포넌트
                dcc.Interval(
                    id="interval-component",
                    interval=1000,  # 1초마다 업데이트
                    n_intervals=0,
                ),
                # 데이터 저장소
                dcc.Store(id="data-store"),
            ]
        )

    def setup_callbacks(self):
        """콜백 함수들 설정"""

        @self.app.callback(
            Output("connection-status", "children"),
            [Input("connect-btn", "n_clicks"), Input("disconnect-btn", "n_clicks")],
            [State("serial-port-input", "value")],
        )
        def handle_connection(connect_clicks, disconnect_clicks, port):
            """시리얼 연결 처리"""
            ctx = dash.callback_context
            if not ctx.triggered:
                return "연결되지 않음"

            button_id = ctx.triggered[0]["prop_id"].split(".")[0]

            if button_id == "connect-btn" and connect_clicks > 0:
                return self.connect_serial(port)
            elif button_id == "disconnect-btn" and disconnect_clicks > 0:
                return self.disconnect_serial()

            return "연결되지 않음"

        @self.app.callback(
            [
                Output("voltage-graph", "figure"),
                Output("current-graph", "figure"),
                Output("power-graph", "figure"),
                Output("current-values", "children"),
                Output("statistics-panel", "children"),
            ],
            [Input("interval-component", "n_intervals")],
        )
        def update_dashboard(n):
            """대시보드 업데이트"""
            # 큐에서 새 데이터 가져오기
            self.process_data_queue()

            if self.data_buffer.empty:
                # 데이터가 없을 때 빈 그래프 반환
                empty_fig = go.Figure()
                empty_fig.update_layout(title="데이터 없음")

                return (
                    empty_fig,
                    empty_fig,
                    empty_fig,
                    "데이터를 수집 중...",
                    "통계 데이터 없음",
                )

            # 최근 데이터만 표시 (최대 100개 포인트)
            recent_data = self.data_buffer.tail(100).copy()

            # 그래프 생성
            voltage_fig = self.create_voltage_graph(recent_data)
            current_fig = self.create_current_graph(recent_data)
            power_fig = self.create_power_graph(recent_data)

            # 현재 값 표시
            current_values = self.create_current_values_display(recent_data)

            # 통계 정보
            statistics = self.create_statistics_panel(recent_data)

            return voltage_fig, current_fig, power_fig, current_values, statistics

    def connect_serial(self, port):
        """시리얼 포트 연결"""
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()

            self.serial_port = serial.Serial(port, 115200, timeout=1)
            self.is_collecting = True

            # 데이터 수집 스레드 시작
            self.data_thread = threading.Thread(target=self.collect_data, daemon=True)
            self.data_thread.start()

            return f"✅ {port}에 연결됨"

        except Exception as e:
            return f"❌ 연결 실패: {str(e)}"

    def disconnect_serial(self):
        """시리얼 포트 연결 해제"""
        try:
            self.is_collecting = False
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
            return "연결 해제됨"
        except Exception as e:
            return f"연결 해제 오류: {str(e)}"

    def collect_data(self):
        """시리얼 포트에서 데이터 수집"""
        while self.is_collecting and self.serial_port and self.serial_port.is_open:
            try:
                line = self.serial_port.readline().decode("utf-8").strip()
                if line and "," in line:
                    # CSV 형식 파싱: timestamp,voltage,current,power
                    parts = line.split(",")
                    if len(parts) == 4:
                        timestamp = datetime.now()
                        voltage = float(parts[1])
                        current = float(parts[2])
                        power = float(parts[3])

                        data_point = {
                            "timestamp": timestamp,
                            "voltage": voltage,
                            "current": current,
                            "power": power,
                        }

                        self.data_queue.put(data_point)

            except Exception as e:
                print(f"데이터 수집 오류: {e}")
                time.sleep(0.1)

    def process_data_queue(self):
        """큐에서 데이터를 가져와 버퍼에 추가"""
        while not self.data_queue.empty():
            try:
                data_point = self.data_queue.get_nowait()
                new_row = pd.DataFrame([data_point])
                self.data_buffer = pd.concat(
                    [self.data_buffer, new_row], ignore_index=True
                )

                # 버퍼 크기 제한
                if len(self.data_buffer) > self.max_buffer_size:
                    self.data_buffer = self.data_buffer.tail(self.max_buffer_size)

            except queue.Empty:
                break

    def create_voltage_graph(self, data):
        """전압 그래프 생성"""
        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=data["timestamp"],
                y=data["voltage"],
                mode="lines+markers",
                name="전압 (V)",
                line={"color": "blue", "width": 2},
                marker={"size": 4},
            )
        )

        fig.update_layout(
            title="전압 (V)",
            xaxis_title="시간",
            yaxis_title="전압 (V)",
            hovermode="x unified",
        )

        return fig

    def create_current_graph(self, data):
        """전류 그래프 생성"""
        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=data["timestamp"],
                y=data["current"],
                mode="lines+markers",
                name="전류 (mA)",
                line={"color": "red", "width": 2},
                marker={"size": 4},
            )
        )

        fig.update_layout(
            title="전류 (mA)",
            xaxis_title="시간",
            yaxis_title="전류 (mA)",
            hovermode="x unified",
        )

        return fig

    def create_power_graph(self, data):
        """전력 그래프 생성"""
        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=data["timestamp"],
                y=data["power"],
                mode="lines+markers",
                name="전력 (mW)",
                line={"color": "green", "width": 2},
                marker={"size": 4},
            )
        )

        fig.update_layout(
            title="전력 (mW)",
            xaxis_title="시간",
            yaxis_title="전력 (mW)",
            hovermode="x unified",
        )

        return fig

    def create_current_values_display(self, data):
        """현재 측정값 표시"""
        if data.empty:
            return "데이터 없음"

        latest = data.iloc[-1]

        return html.Div(
            [
                html.Div(
                    [html.H4(f"{latest['voltage']:.3f} V"), html.P("전압")],
                    className="value-box voltage",
                ),
                html.Div(
                    [html.H4(f"{latest['current']:.2f} mA"), html.P("전류")],
                    className="value-box current",
                ),
                html.Div(
                    [html.H4(f"{latest['power']:.2f} mW"), html.P("전력")],
                    className="value-box power",
                ),
            ],
            className="values-container",
        )

    def create_statistics_panel(self, data):
        """통계 정보 패널 생성"""
        if data.empty:
            return "통계 데이터 없음"

        stats = {
            "voltage": {
                "avg": data["voltage"].mean(),
                "min": data["voltage"].min(),
                "max": data["voltage"].max(),
                "std": data["voltage"].std(),
            },
            "current": {
                "avg": data["current"].mean(),
                "min": data["current"].min(),
                "max": data["current"].max(),
                "std": data["current"].std(),
            },
            "power": {
                "avg": data["power"].mean(),
                "min": data["power"].min(),
                "max": data["power"].max(),
                "std": data["power"].std(),
            },
        }

        return html.Div(
            [
                html.Div(
                    [
                        html.H5("전압 통계"),
                        html.P(f"평균: {stats['voltage']['avg']:.3f} V"),
                        html.P(f"최소: {stats['voltage']['min']:.3f} V"),
                        html.P(f"최대: {stats['voltage']['max']:.3f} V"),
                        html.P(f"표준편차: {stats['voltage']['std']:.3f} V"),
                    ],
                    className="stat-box",
                ),
                html.Div(
                    [
                        html.H5("전류 통계"),
                        html.P(f"평균: {stats['current']['avg']:.2f} mA"),
                        html.P(f"최소: {stats['current']['min']:.2f} mA"),
                        html.P(f"최대: {stats['current']['max']:.2f} mA"),
                        html.P(f"표준편차: {stats['current']['std']:.2f} mA"),
                    ],
                    className="stat-box",
                ),
                html.Div(
                    [
                        html.H5("전력 통계"),
                        html.P(f"평균: {stats['power']['avg']:.2f} mW"),
                        html.P(f"최소: {stats['power']['min']:.2f} mW"),
                        html.P(f"최대: {stats['power']['max']:.2f} mW"),
                        html.P(f"표준편차: {stats['power']['std']:.2f} mW"),
                    ],
                    className="stat-box",
                ),
            ],
            className="statistics-grid",
        )

    def run(self, debug=True, host="127.0.0.1", port=8050):
        """대시보드 실행"""
        print("🚀 INA219 Power Monitoring Dashboard 시작")
        print(f"📊 대시보드 URL: http://{host}:{port}")
        print("🔌 Arduino를 연결하고 시리얼 포트를 설정하세요")

        self.app.run_server(debug=debug, host=host, port=port)


def main():
    """메인 함수"""
    dashboard = PowerMonitoringDashboard()
    dashboard.run(debug=True, host="0.0.0.0", port=8050)


if __name__ == "__main__":
    main()
