#!/usr/bin/env python3
"""
Phase 2.1 WebSocket 실시간 통신 테스트
최소한의 구현으로 단계별 테스트
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


class Phase2Tester:
    """Phase 2.1 테스터"""

    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.ws_url = server_url.replace("http", "ws") + "/ws"
        self.messages_received = 0
        self.test_duration = 30  # 30초 테스트

    async def test_server_status(self):
        """서버 상태 테스트"""
        print("🔍 Testing server status...")

        try:
            response = requests.get(f"{self.server_url}/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Server status: {data}")
                return True
            else:
                print(f"❌ Server returned status code: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Failed to connect to server: {e}")
            return False

    async def test_websocket_connection(self):
        """WebSocket 연결 테스트"""
        print(f"🔗 Testing WebSocket connection to {self.ws_url}...")

        try:
            async with websockets.connect(self.ws_url) as websocket:
                print("✅ WebSocket connected successfully")

                # 연결 유지 테스트 (5초)
                start_time = time.time()
                while time.time() - start_time < 5:
                    try:
                        # 1초 타임아웃으로 메시지 수신 시도
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        self.messages_received += 1

                        # 메시지 파싱
                        try:
                            data = json.loads(message)
                            if data.get("type") == "measurement":
                                measurement = data["data"]
                                print(
                                    f"📊 Data: V={measurement['v']:.3f}V, "
                                    f"A={measurement['a']:.3f}A, "
                                    f"W={measurement['w']:.3f}W"
                                )
                            elif data.get("type") == "status":
                                print(f"📢 Status: {data['message']}")
                        except json.JSONDecodeError:
                            print(f"📨 Raw message: {message}")

                    except asyncio.TimeoutError:
                        # 타임아웃은 정상 (메시지가 없을 수 있음)
                        pass

                print(
                    f"✅ WebSocket test completed. Messages received: {self.messages_received}"
                )
                return True

        except Exception as e:
            print(f"❌ WebSocket connection failed: {e}")
            return False

    async def test_simulator_integration(self):
        """시뮬레이터 통합 테스트"""
        print("🎭 Testing simulator integration...")

        try:
            # 시뮬레이터 시작 요청
            response = requests.post(f"{self.server_url}/simulator/start", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Simulator start response: {data}")
            else:
                print(f"⚠️ Simulator start returned: {response.status_code}")

            # WebSocket으로 데이터 수신 테스트
            print("📡 Testing real-time data stream...")

            async with websockets.connect(self.ws_url) as websocket:
                data_count = 0
                start_time = time.time()

                while time.time() - start_time < 10 and data_count < 10:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        data = json.loads(message)

                        if data.get("type") == "measurement":
                            data_count += 1
                            measurement = data["data"]
                            print(
                                f"  📈 Sample {data_count}: "
                                f"V={measurement['v']:.3f}V, "
                                f"A={measurement['a']:.3f}A, "
                                f"W={measurement['w']:.3f}W, "
                                f"Seq={measurement['seq']}"
                            )

                    except asyncio.TimeoutError:
                        print("  ⏰ Waiting for data...")
                    except json.JSONDecodeError:
                        pass

                if data_count > 0:
                    print(f"✅ Received {data_count} measurement samples")
                    return True
                else:
                    print("❌ No measurement data received")
                    return False

        except Exception as e:
            print(f"❌ Simulator integration test failed: {e}")
            return False

    async def test_performance(self):
        """성능 테스트"""
        print(f"🚀 Testing performance for {self.test_duration} seconds...")

        try:
            async with websockets.connect(self.ws_url) as websocket:
                start_time = time.time()
                message_count = 0
                measurement_count = 0
                last_seq = -1
                gaps = 0

                while time.time() - start_time < self.test_duration:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        message_count += 1

                        data = json.loads(message)
                        if data.get("type") == "measurement":
                            measurement_count += 1
                            seq = data["data"].get("seq", 0)

                            # 시퀀스 갭 체크
                            if last_seq >= 0 and seq != last_seq + 1:
                                gaps += 1
                            last_seq = seq

                    except asyncio.TimeoutError:
                        pass
                    except json.JSONDecodeError:
                        pass

                # 성능 결과
                elapsed = time.time() - start_time
                message_rate = message_count / elapsed
                measurement_rate = measurement_count / elapsed

                print("📊 Performance Results:")
                print(f"  Duration: {elapsed:.1f}s")
                print(f"  Total messages: {message_count}")
                print(f"  Measurement data: {measurement_count}")
                print(f"  Message rate: {message_rate:.1f}/sec")
                print(f"  Measurement rate: {measurement_rate:.1f}/sec")
                print(f"  Sequence gaps: {gaps}")

                # 성능 평가
                if measurement_rate >= 0.8:  # 최소 0.8 samples/sec
                    print("✅ Performance test PASSED")
                    return True
                else:
                    print("❌ Performance test FAILED")
                    return False

        except Exception as e:
            print(f"❌ Performance test failed: {e}")
            return False

    async def run_all_tests(self):
        """모든 테스트 실행"""
        print("=" * 60)
        print("🧪 Phase 2.1 WebSocket Real-time Communication Test")
        print("=" * 60)

        tests = [
            ("Server Status", self.test_server_status),
            ("WebSocket Connection", self.test_websocket_connection),
            ("Simulator Integration", self.test_simulator_integration),
            ("Performance", self.test_performance),
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
            print("🎉 All tests PASSED! Phase 2.1 implementation is working correctly.")
        else:
            print("⚠️ Some tests FAILED. Please check the implementation.")

        return passed == total


async def main():
    """메인 함수"""
    print("🚀 Starting Phase 2.1 WebSocket Test...")
    print("📝 Make sure the server is running: python src/python/backend/main.py")
    print()

    # 서버 시작 대기
    print("⏳ Waiting for server to start...")
    await asyncio.sleep(2)

    tester = Phase2Tester()
    success = await tester.run_all_tests()

    if success:
        print("\n🎊 Phase 2.1 WebSocket implementation is ready!")
        print(
            "🌐 Open test_websocket.html in your browser to see the real-time dashboard"
        )
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
