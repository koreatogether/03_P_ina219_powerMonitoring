#!/usr/bin/env python3
"""
Phase 4.1 데이터 분석 & 이상치 탐지 테스트
"""

import asyncio
import json
import os
import sys
import time

import numpy as np

# 경로 설정
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

try:
    import requests
    import websockets
except ImportError:
    print("❌ Required packages not installed. Run:")
    print("pip install websockets requests numpy")
    sys.exit(1)

from data_analyzer import DataAnalyzer


class Phase41Tester:
    """Phase 4.1 데이터 분석 테스터"""

    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.ws_url = server_url.replace("http", "ws") + "/ws"
        self.test_duration = 60  # 1분 테스트

    async def test_data_analyzer_standalone(self):
        """독립 데이터 분석기 테스트"""
        print("🔍 Testing standalone data analyzer...")

        analyzer = DataAnalyzer(":memory:")  # 메모리 DB 사용

        # 정상 데이터 추가 (50개)
        print("  📊 Adding normal data samples...")
        normal_count = 0
        for _i in range(50):
            voltage = 5.0 + np.random.normal(0, 0.02)
            current = 0.25 + np.random.normal(0, 0.01)
            power = voltage * current

            result = analyzer.analyze_data_point(voltage, current, power)
            if result["has_any_outlier"]:
                normal_count += 1

        print(f"    Normal data outliers: {normal_count}/50")

        # 이상치 데이터 추가
        print("  🚨 Adding outlier data samples...")
        outlier_data = [
            (6.5, 0.25, 1.625),  # 전압 이상치
            (5.0, 0.8, 4.0),  # 전류 이상치
            (5.0, 0.25, 2.5),  # 전력 이상치
            (3.0, 0.25, 0.75),  # 전압 저하
            (5.0, 0.05, 0.25),  # 전류 저하
        ]

        detected_outliers = 0
        for voltage, current, power in outlier_data:
            result = analyzer.analyze_data_point(voltage, current, power)
            if result["has_any_outlier"]:
                detected_outliers += 1
                print(
                    f"    ✅ Detected outlier: V={voltage}V, A={current}A, W={power}W"
                )
            else:
                print(f"    ❌ Missed outlier: V={voltage}V, A={current}A, W={power}W")

        # 통계 요약
        summary = analyzer.get_outlier_summary()
        print("  📈 Analysis Summary:")
        print(f"    Total samples: {summary['overall']['total_samples']}")
        print(f"    Total outliers: {summary['overall']['total_outliers']}")
        print(
            f"    Overall outlier rate: {summary['overall']['overall_outlier_rate']}%"
        )

        # 성공 기준: 이상치 5개 중 최소 3개 탐지
        success = detected_outliers >= 3
        print(f"  🎯 Outlier detection: {detected_outliers}/5 detected")

        return success

    async def test_analysis_api_endpoints(self):
        """분석 API 엔드포인트 테스트"""
        print("🌐 Testing analysis API endpoints...")

        endpoints = [
            ("/api/analysis/outliers/summary", "Outlier Summary"),
            ("/api/analysis/outliers/recent?limit=5", "Recent Outliers"),
            ("/api/analysis/moving-averages", "Moving Averages"),
            ("/api/analysis/history?hours=1", "Analysis History"),
        ]

        success_count = 0

        for endpoint, name in endpoints:
            try:
                response = requests.get(f"{self.server_url}{endpoint}", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    print(f"  ✅ {name}: OK")

                    # 데이터 구조 검증
                    if "data" in data and "timestamp" in data:
                        success_count += 1
                    else:
                        print("    ⚠️ Invalid response structure")
                else:
                    print(f"  ❌ {name}: HTTP {response.status_code}")

            except Exception as e:
                print(f"  ❌ {name}: {e}")

        print(f"  🎯 API endpoints: {success_count}/{len(endpoints)} working")
        return success_count == len(endpoints)

    async def test_realtime_analysis_integration(self):
        """실시간 분석 통합 테스트"""
        print("📡 Testing real-time analysis integration...")

        try:
            async with websockets.connect(self.ws_url) as websocket:
                analysis_data_count = 0
                outlier_detected_count = 0
                start_time = time.time()

                print("  📊 Monitoring real-time analysis data...")

                while time.time() - start_time < 30:  # 30초 테스트
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        data = json.loads(message)

                        if data.get("type") == "measurement" and "analysis" in data:
                            analysis_data_count += 1
                            analysis = data["analysis"]

                            # 분석 데이터 구조 검증
                            required_fields = [
                                "has_outlier",
                                "outlier_count",
                                "confidence",
                                "moving_averages",
                            ]
                            if all(field in analysis for field in required_fields):
                                if analysis["has_outlier"]:
                                    outlier_detected_count += 1
                                    print(
                                        f"    🚨 Outlier detected: {analysis['outlier_count']} metrics"
                                    )

                            if analysis_data_count % 10 == 0:
                                print(
                                    f"    📈 Analysis samples: {analysis_data_count}, Outliers: {outlier_detected_count}"
                                )

                    except asyncio.TimeoutError:
                        continue
                    except json.JSONDecodeError:
                        continue

                print("  📊 Results:")
                print(f"    Analysis samples: {analysis_data_count}")
                print(f"    Outliers detected: {outlier_detected_count}")
                print(f"    Analysis rate: {analysis_data_count / 30:.1f} samples/sec")

                # 성공 기준: 최소 20개 분석 샘플 수신
                success = analysis_data_count >= 20
                return success

        except Exception as e:
            print(f"  ❌ WebSocket test failed: {e}")
            return False

    async def test_moving_averages_accuracy(self):
        """이동평균 정확도 테스트"""
        print("📈 Testing moving averages accuracy...")

        analyzer = DataAnalyzer(":memory:")

        # 알려진 패턴의 데이터 생성
        test_values = [5.0] * 60  # 60개의 동일한 값

        print("  📊 Adding constant values for moving average test...")
        for value in test_values:
            analyzer.analyze_data_point(value, 0.25, value * 0.25)

        # 이동평균 확인
        averages = analyzer.moving_avg_calc.get_all_moving_averages()

        print("  📈 Moving averages:")
        for metric, avg_dict in averages.items():
            print(
                f"    {metric}: 1m={avg_dict['1m']:.3f}, 5m={avg_dict['5m']:.3f}, 15m={avg_dict['15m']:.3f}"
            )

        # 정확도 검증 (상수 값이므로 모든 이동평균이 동일해야 함)
        voltage_avgs = averages["voltage"]
        accuracy_check = (
            abs(voltage_avgs["1m"] - 5.0) < 0.001
            and abs(voltage_avgs["5m"] - 5.0) < 0.001
            and abs(voltage_avgs["15m"] - 5.0) < 0.001
        )

        print(f"  🎯 Accuracy check: {'✅ PASS' if accuracy_check else '❌ FAIL'}")
        return accuracy_check

    async def test_outlier_detection_methods(self):
        """이상치 탐지 방법 테스트"""
        print("🚨 Testing outlier detection methods...")

        from data_analyzer import OutlierDetector

        detector = OutlierDetector()

        # 정상 데이터로 기준 설정
        normal_data = [5.0 + np.random.normal(0, 0.02) for _ in range(100)]
        for value in normal_data:
            detector.add_data(value, 0.25, value * 0.25)

        # 이상치 테스트
        test_cases = [
            (5.0, False, "Normal value"),
            (6.0, True, "High voltage outlier"),
            (3.5, True, "Low voltage outlier"),
            (5.5, True, "Moderate outlier"),
        ]

        z_score_success = 0
        iqr_success = 0

        print("  🔍 Testing detection methods:")
        for value, should_be_outlier, description in test_cases:
            z_outlier, z_score = detector.detect_outliers_zscore("voltage", value)
            iqr_outlier, iqr_score = detector.detect_outliers_iqr("voltage", value)

            z_correct = z_outlier == should_be_outlier
            iqr_correct = iqr_outlier == should_be_outlier

            if z_correct:
                z_score_success += 1
            if iqr_correct:
                iqr_success += 1

            print(
                f"    {description}: Z-score={'✅' if z_correct else '❌'} IQR={'✅' if iqr_correct else '❌'}"
            )

        print("  📊 Method accuracy:")
        print(f"    Z-score: {z_score_success}/{len(test_cases)} correct")
        print(f"    IQR: {iqr_success}/{len(test_cases)} correct")

        # 성공 기준: 두 방법 모두 75% 이상 정확도
        success = z_score_success >= 3 and iqr_success >= 3
        return success

    async def run_all_tests(self):
        """모든 테스트 실행"""
        print("=" * 60)
        print("🧪 Phase 4.1 Data Analysis & Outlier Detection Test")
        print("=" * 60)

        tests = [
            ("Standalone Data Analyzer", self.test_data_analyzer_standalone),
            ("Moving Averages Accuracy", self.test_moving_averages_accuracy),
            ("Outlier Detection Methods", self.test_outlier_detection_methods),
            ("Analysis API Endpoints", self.test_analysis_api_endpoints),
            ("Real-time Analysis Integration", self.test_realtime_analysis_integration),
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
            print("🎉 All tests PASSED! Phase 4.1 data analysis is working correctly.")
            print("🔍 Features verified:")
            print("  • Moving averages calculation (1m, 5m, 15m)")
            print("  • Outlier detection (Z-score & IQR methods)")
            print("  • Real-time analysis integration")
            print("  • Analysis API endpoints")
            print("🌐 Open http://localhost:8000 to see the analysis dashboard!")
        else:
            print("⚠️ Some tests FAILED. Please check the implementation.")

        return passed == total


async def main():
    """메인 함수"""
    print("🚀 Starting Phase 4.1 Data Analysis Test...")
    print("📝 Make sure the server is running: python src/python/backend/main.py")
    print()

    # 서버 시작 대기
    print("⏳ Waiting for server to start...")
    await asyncio.sleep(2)

    tester = Phase41Tester()
    success = await tester.run_all_tests()

    if success:
        print("\n🎊 Phase 4.1 Data Analysis implementation is ready!")
        print("🔍 Advanced features now available:")
        print("  • Real-time moving averages")
        print("  • Intelligent outlier detection")
        print("  • Analysis confidence scoring")
        print("  • Comprehensive analysis APIs")
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
