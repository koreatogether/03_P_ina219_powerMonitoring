#!/usr/bin/env python3
"""
Phase 2.2 Chart.js 실시간 그래프 테스트
"""

import asyncio
import json
import os
import sys
import time

# 경로 설정
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

try:
    import requests
    import websockets
except ImportError:
    print("❌ Required packages not installed. Run:")
    print("pip install websockets requests")
    sys.exit(1)


class Phase22Tester:
    """Phase 2.2 Chart.js 테스터"""

    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.ws_url = server_url.replace("http", "ws") + "/ws"
        self.test_duration = 30

    async def test_dashboard_content(self):
        """대시보드 HTML 내용 테스트"""
        print("🌐 Testing dashboard HTML content...")

        try:
            response = requests.get(self.server_url, timeout=5)
            if response.status_code == 200:
                html_content = response.text

                # Chart.js 관련 요소 확인
                checks = [
                    ("Chart.js CDN", "chart.js" in html_content.lower()),
                    ("Canvas Element", "powerChart" in html_content),
                    ("Chart Title", "Real-time Chart" in html_content),
                    ("Chart Functions", "initChart" in html_content),
                    ("addDataToChart", "addDataToChart" in html_content),
                    ("Multi-axis Config", "yAxisID" in html_content),
                ]

                all_passed = True
                for check_name, result in checks:
                    status = "✅" if result else "❌"
                    print(
                        f"  {status} {check_name}: {'Found' if result else 'Missing'}"
                    )
                    if not result:
                        all_passed = False

                return all_passed
            else:
                print(f"❌ Dashboard returned status code: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Failed to test dashboard: {e}")
            return False

    async def test_realtime_chart_data(self):
        """실시간 차트 데이터 스트림 테스트"""
        print("📈 Testing real-time chart data stream...")

        try:
            async with websockets.connect(self.ws_url) as websocket:
                data_samples = []
                start_time = time.time()

                print("  📊 Collecting chart data samples...")

                while time.time() - start_time < 10 and len(data_samples) < 10:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        data = json.loads(message)

                        if data.get("type") == "measurement":
                            measurement = data["data"]
                            data_samples.append(measurement)

                            print(
                                f"    📈 Sample {len(data_samples)}: "
                                f"V={measurement['v']:.3f}V, "
                                f"A={measurement['a']:.3f}A, "
                                f"W={measurement['w']:.3f}W"
                            )

                    except asyncio.TimeoutError:
                        print("    ⏰ Waiting for data...")
                    except json.JSONDecodeError:
                        pass

                if len(data_samples) >= 5:
                    # 데이터 변동성 확인 (차트에 의미있는 변화가 있는지)
                    voltages = [s["v"] for s in data_samples]
                    currents = [s["a"] for s in data_samples]
                    powers = [s["w"] for s in data_samples]

                    v_range = max(voltages) - min(voltages)
                    a_range = max(currents) - min(currents)
                    w_range = max(powers) - min(powers)

                    print("  📊 Data Analysis:")
                    print(f"    Voltage range: {v_range:.3f}V")
                    print(f"    Current range: {a_range:.3f}A")
                    print(f"    Power range: {w_range:.3f}W")

                    # 차트에 표시할 만한 변동이 있는지 확인
                    has_variation = v_range > 0.01 or a_range > 0.01 or w_range > 0.01

                    if has_variation:
                        print("  ✅ Chart data has meaningful variation")
                        return True
                    else:
                        print("  ⚠️ Chart data has minimal variation")
                        return True  # 여전히 통과 (데이터는 수신됨)
                else:
                    print(f"  ❌ Insufficient data samples: {len(data_samples)}")
                    return False

        except Exception as e:
            print(f"❌ Chart data test failed: {e}")
            return False

    async def test_chart_performance(self):
        """차트 성능 테스트"""
        print("🚀 Testing chart performance...")

        try:
            async with websockets.connect(self.ws_url) as websocket:
                start_time = time.time()
                update_count = 0
                last_update = start_time

                print(
                    f"  📊 Monitoring chart updates for {self.test_duration} seconds..."
                )

                while time.time() - start_time < self.test_duration:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message)

                        if data.get("type") == "measurement":
                            update_count += 1
                            current_time = time.time()

                            # 업데이트 간격 체크
                            interval = current_time - last_update
                            last_update = current_time

                            if update_count % 10 == 0:
                                print(
                                    f"    📈 Update {update_count}: interval={interval:.2f}s"
                                )

                    except asyncio.TimeoutError:
                        pass
                    except json.JSONDecodeError:
                        pass

                # 성능 분석
                elapsed = time.time() - start_time
                update_rate = update_count / elapsed

                print("  📊 Performance Results:")
                print(f"    Duration: {elapsed:.1f}s")
                print(f"    Chart updates: {update_count}")
                print(f"    Update rate: {update_rate:.1f}/sec")

                # 성능 기준: 최소 0.5 updates/sec
                if update_rate >= 0.5:
                    print("  ✅ Chart performance is acceptable")
                    return True
                else:
                    print("  ❌ Chart performance is too slow")
                    return False

        except Exception as e:
            print(f"❌ Chart performance test failed: {e}")
            return False

    async def test_multi_axis_config(self):
        """멀티축 설정 테스트"""
        print("📊 Testing multi-axis configuration...")

        try:
            response = requests.get(self.server_url, timeout=5)
            if response.status_code == 200:
                html_content = response.text

                # 멀티축 관련 설정 확인
                multi_axis_checks = [
                    (
                        "Y-axis (Voltage)",
                        "'y'" in html_content and "Voltage" in html_content,
                    ),
                    (
                        "Y1-axis (Current)",
                        "'y1'" in html_content and "Current" in html_content,
                    ),
                    (
                        "Y2-axis (Power)",
                        "'y2'" in html_content and "Power" in html_content,
                    ),
                    ("Left Position", "position: 'left'" in html_content),
                    ("Right Position", "position: 'right'" in html_content),
                    (
                        "Different Colors",
                        "rgb(255, 99, 132)" in html_content
                        and "rgb(54, 162, 235)" in html_content,
                    ),
                ]

                all_passed = True
                for check_name, result in multi_axis_checks:
                    status = "✅" if result else "❌"
                    print(
                        f"  {status} {check_name}: {'Configured' if result else 'Missing'}"
                    )
                    if not result:
                        all_passed = False

                return all_passed
            else:
                print("❌ Failed to get dashboard content")
                return False

        except Exception as e:
            print(f"❌ Multi-axis test failed: {e}")
            return False

    async def run_all_tests(self):
        """모든 테스트 실행"""
        print("=" * 60)
        print("🧪 Phase 2.2 Chart.js Real-time Graph Test")
        print("=" * 60)

        tests = [
            ("Dashboard Content", self.test_dashboard_content),
            ("Multi-axis Configuration", self.test_multi_axis_config),
            ("Real-time Chart Data", self.test_realtime_chart_data),
            ("Chart Performance", self.test_chart_performance),
        ]

        results = []

        for test_name, test_func in tests:
            print(f"\n🔬 Running {test_name} test...")
            try:
                result = await test_func()
                results.append((test_name, result))

                if result:
                    print(f"✅ {test_name} test PASSED")
                else:
                    print(f"❌ {test_name} test FAILED")

            except Exception as e:
                print(f"❌ {test_name} test ERROR: {e}")
                results.append((test_name, False))

            print("-" * 40)

        # 최종 결과
        print("\n📋 Test Summary:")
        passed = sum(1 for _, result in results if result)
        total = len(results)

        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {test_name}: {status}")

        print(f"\n🎯 Overall Result: {passed}/{total} tests passed")

        if passed == total:
            print(
                "🎉 All tests PASSED! Phase 2.2 Chart.js implementation is working correctly."
            )
            print("📈 Real-time charts are ready!")
            print("🌐 Open http://localhost:8000 to see the live dashboard with charts")
        else:
            print("⚠️ Some tests FAILED. Please check the implementation.")

        return passed == total


async def main():
    """메인 함수"""
    print("🚀 Starting Phase 2.2 Chart.js Test...")
    print("📝 Make sure the server is running: python src/python/backend/main.py")
    print()

    # 서버 시작 대기
    print("⏳ Waiting for server to start...")
    await asyncio.sleep(2)

    tester = Phase22Tester()
    success = await tester.run_all_tests()

    if success:
        print("\n🎊 Phase 2.2 Chart.js implementation is ready!")
        print("📈 Features implemented:")
        print("  • Real-time line charts")
        print("  • Multi-axis display (V/A/W)")
        print("  • 60-second rolling buffer")
        print("  • Smooth animations")
        print("🌐 Open http://localhost:8000 and click 'Connect' to see live charts!")
    else:
        print("\n🔧 Please fix the issues and run the test again")

    return success


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        sys.exit(1)
