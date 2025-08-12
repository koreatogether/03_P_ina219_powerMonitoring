### 중간 통신 설계
Arduino에서 INA219 센서로 측정한 W(전력), V(전압), A(전류) 데이터를 Python Dash 대시보드로 전달하기 위해, 가장 심플한 방식으로 시리얼 통신(USB)을 사용하겠습니다. 이는 추가 하드웨어 없이 Arduino가 PC와 연결된 상태에서 데이터를 전송할 수 있게 합니다. (Bluetooth나 Wi-Fi 같은 복잡한 네트워킹은 피함)

- **데이터 전송 형식**: Arduino가 주기적으로 (예: 1초마다) 간단한 문자열을 시리얼 포트로 보냅니다. 형식은 CSV 스타일로 유지하여 파싱이 쉽도록: `"W:10.5,V:5.0,A:2.1\n"`. 이는 문자열로 직렬화되어 전송되며, Python 쪽에서 쉽게 split하거나 parse할 수 있습니다. 만약 데이터가 더 많아지면 JSON으로 확장 가능하지만, 심플하게 CSV로 제한.
  
- **통신 흐름**:
  1. Arduino: INA219에서 값을 읽고, Serial.println()으로 문자열 전송. (예: Serial.println(String("W:") + power + ",V:" + voltage + ",A:" + current);)
  2. Python 쪽: `serial` 라이브러리를 사용해 COM 포트(또는 /dev/ttyUSB0 등)를 열고, 데이터를 읽음. 읽은 데이터를 버퍼에 저장하거나 바로 Dash 콜백으로 전달.
  3. 에러 핸들링: 데이터가 누락되면 이전 값을 유지하거나 "N/A" 표시. 재연결 로직은 최소화 (포트가 열리지 않으면 로그만 남김).
  4. 주기: Arduino에서 500ms~1s 간격으로 전송. Python에서 별도 스레드로 읽어 Dash의 메인 스레드와 충돌 피함 (threading 사용).

이 설계는 중간 계층(예: MQTT 브로커나 데이터베이스) 없이 직접 연결되어 심플합니다. 만약 원격이 필요하면 나중에 Flask나 Socket으로 확장 가능하지만, 지금은 로컬 시리얼로 충분.

### 대시보드 쪽 설계 (Python Dash)
Dash를 사용해 웹 기반 대시보드를 만듭니다. 목표는 실시간 데이터 표시만: 현재 값 텍스트 + 시간에 따른 선 그래프. 복잡한 상호작용(메뉴, 필터링)은 생략하고, 자동 업데이트만 구현. Dash의 Interval 컴포넌트로 1초마다 데이터 refresh.

- **주요 컴포넌트**:
  - **현재 값 표시**: 3개의 텍스트 박스 (W, V, A). 크고 bold한 폰트로 시각화.
  - **그래프**: 하나의 Plotly 선 그래프에 W/V/A를 동시에 플롯 (색상 구분). x축은 시간(최근 1분 데이터만 유지, deque로 버퍼링), y축은 자동 스케일링.
  - **업데이트 메커니즘**: Interval로 트리거되어 시리얼에서 최신 데이터 읽음. 데이터는 글로벌 변수나 deque로 저장 (최대 60개 포인트로 메모리 절약).

- **필요 라이브러리**: dash, plotly, serial, threading, collections (deque).

- **코드 구조 스케치** (실행 가능한 최소 예시, 실제로는 app.py 파일로 저장 후 `python app.py`로 웹서버 실행):
  ```python
  import dash
  from dash import dcc, html, Input, Output
  import plotly.graph_objs as go
  from collections import deque
  import serial
  import threading
  import time

  # 글로벌 데이터 버퍼 (최근 60포인트, 1분 데이터)
  MAX_LEN = 60
  times = deque(maxlen=MAX_LEN)
  powers = deque(maxlen=MAX_LEN)  # W
  voltages = deque(maxlen=MAX_LEN)  # V
  currents = deque(maxlen=MAX_LEN)  # A

  # 시리얼 포트 설정 (포트는 실제로 변경, e.g., 'COM3' 또는 '/dev/ttyUSB0')
  ser = serial.Serial('COM3', 9600, timeout=1)
  latest_data = {'W': 0.0, 'V': 0.0, 'A': 0.0}

  # 별도 스레드로 시리얼 데이터 읽기 (Dash 메인 스레드 블록 방지)
  def read_serial():
      while True:
          try:
              line = ser.readline().decode('utf-8').strip()
              if line:
                  parts = line.split(',')
                  data = {}
                  for part in parts:
                      key, val = part.split(':')
                      data[key] = float(val)
                  latest_data.update(data)
                  times.append(time.time())
                  powers.append(data.get('W', 0.0))
                  voltages.append(data.get('V', 0.0))
                  currents.append(data.get('A', 0.0))
          except Exception:
              pass  # 에러 무시, 다음 루프
          time.sleep(0.5)  # 500ms 간격

  threading.Thread(target=read_serial, daemon=True).start()

  # Dash 앱 설정
  app = dash.Dash(__name__)

  app.layout = html.Div([
      html.H1('INA219 Power Monitor Dashboard'),
      html.Div([
          html.Div([html.H3('Power (W)'), html.P(id='power-val', style={'font-size': '24px', 'font-weight': 'bold'})]),
          html.Div([html.H3('Voltage (V)'), html.P(id='voltage-val', style={'font-size': '24px', 'font-weight': 'bold'})]),
          html.Div([html.H3('Current (A)'), html.P(id='current-val', style={'font-size': '24px', 'font-weight': 'bold'})])
      ], style={'display': 'flex', 'justify-content': 'space-around'}),
      dcc.Graph(id='graph'),
      dcc.Interval(id='interval', interval=1000, n_intervals=0)  # 1초 업데이트
  ])

  @app.callback(
      [Output('power-val', 'children'), Output('voltage-val', 'children'), Output('current-val', 'children'),
       Output('graph', 'figure')],
      Input('interval', 'n_intervals')
  )
  def update_dashboard(n):
      # 현재 값
      power_str = f"{latest_data['W']:.2f}"
      voltage_str = f"{latest_data['V']:.2f}"
      current_str = f"{latest_data['A']:.2f}"
      
      # 그래프
      fig = go.Figure()
      fig.add_trace(go.Scatter(x=list(times), y=list(powers), mode='lines', name='Power (W)', line={'color': 'red'}))
      fig.add_trace(go.Scatter(x=list(times), y=list(voltages), mode='lines', name='Voltage (V)', line={'color': 'blue'}))
      fig.add_trace(go.Scatter(x=list(times), y=list(currents), mode='lines', name='Current (A)', line={'color': 'green'}))
      fig.update_layout(title='Real-time W/V/A Graph', xaxis_title='Time', yaxis_title='Value', xaxis={'type': 'date'})
      
      return power_str, voltage_str, current_str, fig

  if __name__ == '__main__':
      app.run_server(debug=True)
  ```

이 설계는 최소 기능으로 유지: 데이터 읽기 → 저장 → 표시. 그래프는 자동 스케일링되며, UI는 간단한 레이아웃. 확장 시 min/max 표시나 필터링 추가 가능하지만, 요청대로 심플하게 끝냄. 웹 브라우저에서 localhost:8050으로 접근해 확인.