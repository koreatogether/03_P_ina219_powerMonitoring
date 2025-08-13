#!/usr/bin/env python3
"""
Phase 3.1 데이터베이스 통합 테스트
SQLite 데이터베이스 저장, 조회, 통계 기능 검증

테스트 항목:
1. 데이터베이스 초기화 및 테이블 생성
2. 측정 데이터 저장 및 조회
3. 1분 통계 저장 및 조회
4. 알림 이벤트 저장 및 조회
5. 48시간 데이터 자동 정리
6. API 엔드포인트 테스트
7. 성능 및 안정성 검증
"""

import asyncio
import os
import sqlite3
import sys
from datetime import datetime, timedelta

import aiohttp

# UTF-8 인코딩 설정
if sys.platform.startswith("win"):
    import codecs

    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
    os.environ["PYTHONIOENCODING"] = "utf-8"

# 데이터베이스 모듈 임포트
from database import PowerDatabase


class Phase31DatabaseTester:
    """Phase 3.1 데이터베이스 테스트 클래스"""

    def __init__(self):
        self.test_results = []
        self.server_url = "http://localhost:8000"
        self.test_db_path = "test_power_monitoring.db"
        self.db = PowerDatabase(self.test_db_path)

    def log_result(self, test_name: str, status: str, details: str = ""):
        """테스트 결과 로깅"""
        result = {
            "test": test_name,
            "status": status,  # ✅ PASS, ❌ FAIL, ⚠️ WARNING
            "details": details,
            "timestamp": datetime.now().isoformat(),
        }
        self.test_results.append(result)

        # 실시간 출력
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} {test_name}: {details}")

    async def test_database_initialization(self):
        """데이터베이스 초기화 테스트"""
        try:
            # 기존 테스트 DB 삭제
            if os.path.exists(self.test_db_path):
                os.remove(self.test_db_path)

            # 새 데이터베이스 초기화
            PowerDatabase(self.test_db_path)

            # 테이블 존재 확인
            with sqlite3.connect(self.test_db_path) as conn:
                cursor = conn.cursor()

                # 테이블 목록 조회
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]

                required_tables = [
                    "power_measurements",
                    "minute_statistics",
                    "alert_events",
                    "system_logs",
                ]

                for table in required_tables:
                    if table in tables:
                        self.log_result(
                            f"테이블 생성: {table}", "PASS", f"{table} 테이블 생성 확인"
                        )
                    else:
                        self.log_result(
                            f"테이블 생성: {table}", "FAIL", f"{table} 테이블 누락"
                        )

                # 인덱스 확인
                cursor.execute("SELECT sql FROM sqlite_master WHERE type='index'")
                indexes = cursor.fetchall()

                if len(indexes) >= 6:  # 최소 6개의 인덱스 기대
                    self.log_result(
                        "인덱스 생성", "PASS", f"{len(indexes)}개 인덱스 생성됨"
                    )
                else:
                    self.log_result(
                        "인덱스 생성", "WARNING", f"인덱스 수가 부족: {len(indexes)}개"
                    )

        except Exception as e:
            self.log_result("데이터베이스 초기화", "FAIL", f"초기화 실패: {e}")

    async def test_measurement_storage(self):
        """측정 데이터 저장 테스트"""
        try:
            # 테스트 데이터 저장
            test_data = [
                (5.02, 0.245, 1.23, 123, "ok", "NORMAL"),
                (4.98, 0.220, 1.10, 124, "ok", "NORMAL"),
                (5.05, 0.260, 1.31, 125, "ok", "NORMAL"),
                (4.95, 0.200, 0.99, 126, "ok", "NORMAL"),
                (5.01, 0.250, 1.25, 127, "ok", "NORMAL"),
            ]

            saved_count = 0
            for voltage, current, power, seq, status, mode in test_data:
                success = await self.db.save_measurement(
                    voltage=voltage,
                    current=current,
                    power=power,
                    sequence_number=seq,
                    sensor_status=status,
                    simulation_mode=mode,
                )
                if success:
                    saved_count += 1

            self.log_result(
                "측정 데이터 저장",
                "PASS" if saved_count == len(test_data) else "FAIL",
                f"{saved_count}/{len(test_data)} 데이터 저장 성공",
            )

            # 데이터 조회 테스트
            measurements = await self.db.get_recent_measurements(hours=1)

            if len(measurements) >= saved_count:
                self.log_result(
                    "측정 데이터 조회", "PASS", f"{len(measurements)}개 데이터 조회됨"
                )
            else:
                self.log_result(
                    "측정 데이터 조회",
                    "FAIL",
                    f"예상 {saved_count}개, 실제 {len(measurements)}개",
                )

            # 데이터 무결성 검증
            if measurements:
                first_measurement = measurements[0]
                required_fields = [
                    "timestamp",
                    "voltage",
                    "current",
                    "power",
                    "sequence_number",
                ]

                missing_fields = [
                    field for field in required_fields if field not in first_measurement
                ]
                if not missing_fields:
                    self.log_result("데이터 무결성", "PASS", "모든 필수 필드 존재")
                else:
                    self.log_result(
                        "데이터 무결성", "FAIL", f"누락 필드: {missing_fields}"
                    )

        except Exception as e:
            self.log_result("측정 데이터 테스트", "FAIL", f"테스트 실패: {e}")

    async def test_minute_statistics(self):
        """1분 통계 테스트"""
        try:
            # 테스트 통계 데이터 생성
            minute_timestamp = datetime.now().replace(second=0, microsecond=0)

            voltage_stats = {"min": 4.95, "max": 5.05, "avg": 5.00}
            current_stats = {"min": 0.200, "max": 0.260, "avg": 0.230}
            power_stats = {"min": 0.99, "max": 1.31, "avg": 1.15}

            # 통계 저장
            success = await self.db.save_minute_statistics(
                minute_timestamp=minute_timestamp,
                voltage_stats=voltage_stats,
                current_stats=current_stats,
                power_stats=power_stats,
                sample_count=60,
            )

            if success:
                self.log_result("1분 통계 저장", "PASS", "통계 데이터 저장 성공")
            else:
                self.log_result("1분 통계 저장", "FAIL", "통계 데이터 저장 실패")

            # 통계 조회
            statistics = await self.db.get_minute_statistics(hours=1)

            if len(statistics) >= 1:
                self.log_result(
                    "1분 통계 조회", "PASS", f"{len(statistics)}개 통계 조회됨"
                )

                # 통계 데이터 검증
                stat = statistics[0]
                if all(
                    field in stat
                    for field in ["voltage_min", "voltage_max", "voltage_avg"]
                ):
                    self.log_result("통계 데이터 구조", "PASS", "모든 통계 필드 존재")
                else:
                    self.log_result("통계 데이터 구조", "FAIL", "통계 필드 누락")
            else:
                self.log_result("1분 통계 조회", "FAIL", "통계 데이터 조회 실패")

        except Exception as e:
            self.log_result("1분 통계 테스트", "FAIL", f"테스트 실패: {e}")

    async def test_alert_events(self):
        """알림 이벤트 테스트"""
        try:
            # 테스트 알림 저장
            test_alerts = [
                (
                    "threshold_violation",
                    "voltage",
                    4.2,
                    4.5,
                    "danger",
                    "Voltage too low",
                ),
                (
                    "threshold_warning",
                    "current",
                    0.45,
                    0.5,
                    "warning",
                    "Current near limit",
                ),
                ("threshold_violation", "power", 2.5, 2.0, "danger", "Power overload"),
            ]

            saved_count = 0
            for alert_type, metric, value, threshold, severity, message in test_alerts:
                success = await self.db.save_alert_event(
                    alert_type=alert_type,
                    metric_name=metric,
                    metric_value=value,
                    threshold_value=threshold,
                    severity=severity,
                    message=message,
                )
                if success:
                    saved_count += 1

            self.log_result(
                "알림 이벤트 저장",
                "PASS" if saved_count == len(test_alerts) else "FAIL",
                f"{saved_count}/{len(test_alerts)} 알림 저장 성공",
            )

            # 알림 조회
            alerts = await self.db.get_alert_events(hours=1)

            if len(alerts) >= saved_count:
                self.log_result(
                    "알림 이벤트 조회", "PASS", f"{len(alerts)}개 알림 조회됨"
                )
            else:
                self.log_result(
                    "알림 이벤트 조회",
                    "FAIL",
                    f"예상 {saved_count}개, 실제 {len(alerts)}개",
                )

            # severity 필터 테스트
            danger_alerts = await self.db.get_alert_events(hours=1, severity="danger")
            danger_count = len([a for a in test_alerts if a[4] == "danger"])

            if len(danger_alerts) == danger_count:
                self.log_result(
                    "알림 필터링",
                    "PASS",
                    f"danger 알림 {len(danger_alerts)}개 필터링 성공",
                )
            else:
                self.log_result(
                    "알림 필터링",
                    "FAIL",
                    f"예상 {danger_count}개, 실제 {len(danger_alerts)}개",
                )

        except Exception as e:
            self.log_result("알림 이벤트 테스트", "FAIL", f"테스트 실패: {e}")

    async def test_system_logs(self):
        """시스템 로그 테스트"""
        try:
            # 테스트 로그 저장
            test_logs = [
                ("INFO", "server", "Server started", {"version": "3.1.0"}),
                ("WARNING", "database", "High disk usage", {"usage": "85%"}),
                ("ERROR", "simulator", "Connection failed", {"error": "timeout"}),
            ]

            saved_count = 0
            for level, component, message, details in test_logs:
                success = await self.db.save_system_log(
                    level=level, component=component, message=message, details=details
                )
                if success:
                    saved_count += 1

            self.log_result(
                "시스템 로그 저장",
                "PASS" if saved_count == len(test_logs) else "FAIL",
                f"{saved_count}/{len(test_logs)} 로그 저장 성공",
            )

            # 로그 조회
            logs = await self.db.get_system_logs(hours=1)

            if len(logs) >= saved_count:
                self.log_result(
                    "시스템 로그 조회", "PASS", f"{len(logs)}개 로그 조회됨"
                )
            else:
                self.log_result(
                    "시스템 로그 조회",
                    "FAIL",
                    f"예상 {saved_count}개, 실제 {len(logs)}개",
                )

            # 레벨 필터 테스트
            error_logs = await self.db.get_system_logs(hours=1, level="ERROR")
            error_count = len([l for l in test_logs if l[0] == "ERROR"])

            if len(error_logs) == error_count:
                self.log_result(
                    "로그 필터링", "PASS", f"ERROR 로그 {len(error_logs)}개 필터링 성공"
                )
            else:
                self.log_result(
                    "로그 필터링",
                    "FAIL",
                    f"예상 {error_count}개, 실제 {len(error_logs)}개",
                )

        except Exception as e:
            self.log_result("시스템 로그 테스트", "FAIL", f"테스트 실패: {e}")

    async def test_database_cleanup(self):
        """데이터베이스 정리 테스트"""
        try:
            # 오래된 데이터 생성 (50시간 전)
            old_time = datetime.now() - timedelta(hours=50)

            # 직접 DB에 오래된 데이터 삽입
            with sqlite3.connect(self.test_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO power_measurements
                    (timestamp, voltage, current, power, sequence_number, sensor_status, simulation_mode)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (old_time, 5.0, 0.3, 1.5, 999, "ok", "TEST"),
                )
                conn.commit()

            # 정리 전 데이터 수 확인
            measurements_before = await self.db.get_recent_measurements(hours=72)  # 3일
            old_data_count = len(
                [
                    m
                    for m in measurements_before
                    if datetime.fromisoformat(m["timestamp"].replace("Z", ""))
                    < datetime.now() - timedelta(hours=48)
                ]
            )

            # 데이터 정리 실행
            cleanup_stats = await self.db.cleanup_old_data()

            if "error" not in cleanup_stats:
                self.log_result(
                    "데이터 정리 실행", "PASS", f"정리 작업 완료: {cleanup_stats}"
                )
            else:
                self.log_result(
                    "데이터 정리 실행", "FAIL", f"정리 실패: {cleanup_stats['error']}"
                )

            # 정리 후 확인
            measurements_after = await self.db.get_recent_measurements(hours=72)
            remaining_old_count = len(
                [
                    m
                    for m in measurements_after
                    if datetime.fromisoformat(m["timestamp"].replace("Z", ""))
                    < datetime.now() - timedelta(hours=48)
                ]
            )

            if remaining_old_count < old_data_count:
                self.log_result(
                    "오래된 데이터 정리",
                    "PASS",
                    f"정리 전 {old_data_count}개 → 정리 후 {remaining_old_count}개",
                )
            else:
                self.log_result(
                    "오래된 데이터 정리", "WARNING", "오래된 데이터 정리 효과 미확인"
                )

        except Exception as e:
            self.log_result("데이터베이스 정리 테스트", "FAIL", f"테스트 실패: {e}")

    async def test_database_stats(self):
        """데이터베이스 통계 테스트"""
        try:
            stats = await self.db.get_database_stats()

            required_stats = [
                "power_measurements_count",
                "minute_statistics_count",
                "alert_events_count",
                "system_logs_count",
            ]

            missing_stats = [stat for stat in required_stats if stat not in stats]

            if not missing_stats:
                self.log_result(
                    "데이터베이스 통계", "PASS", f"모든 통계 항목 확인: {stats}"
                )
            else:
                self.log_result(
                    "데이터베이스 통계", "FAIL", f"누락 통계: {missing_stats}"
                )

            # 파일 크기 확인
            if "file_size_mb" in stats and stats["file_size_mb"] > 0:
                self.log_result(
                    "DB 파일 크기", "PASS", f"파일 크기: {stats['file_size_mb']:.3f}MB"
                )
            else:
                self.log_result("DB 파일 크기", "WARNING", "파일 크기 정보 없음")

        except Exception as e:
            self.log_result("데이터베이스 통계 테스트", "FAIL", f"테스트 실패: {e}")

    async def test_power_efficiency(self):
        """전력 효율성 분석 테스트"""
        try:
            efficiency = await self.db.calculate_power_efficiency(hours=1)

            required_metrics = [
                "total_energy_wh",
                "avg_voltage",
                "avg_current",
                "avg_power",
                "power_variability_percent",
                "sample_count",
            ]

            missing_metrics = [
                metric for metric in required_metrics if metric not in efficiency
            ]

            if not missing_metrics:
                self.log_result(
                    "전력 효율성 분석", "PASS", f"모든 효율성 메트릭 계산: {efficiency}"
                )
            else:
                self.log_result(
                    "전력 효율성 분석", "FAIL", f"누락 메트릭: {missing_metrics}"
                )

            # 데이터 유효성 검증
            if efficiency.get("sample_count", 0) > 0:
                self.log_result(
                    "효율성 데이터 유효성",
                    "PASS",
                    f"샘플 수: {efficiency['sample_count']}",
                )
            else:
                self.log_result("효율성 데이터 유효성", "WARNING", "분석할 데이터 부족")

        except Exception as e:
            self.log_result("전력 효율성 테스트", "FAIL", f"테스트 실패: {e}")

    async def test_api_endpoints(self):
        """API 엔드포인트 테스트"""
        try:
            # 서버가 실행 중인지 확인
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(f"{self.server_url}/status") as resp:
                        if resp.status == 200:
                            self.log_result("서버 연결", "PASS", "서버 응답 정상")

                            # API 엔드포인트 테스트
                            endpoints = [
                                "/api/measurements",
                                "/api/statistics",
                                "/api/alerts",
                                "/api/logs",
                                "/api/database/stats",
                            ]

                            for endpoint in endpoints:
                                try:
                                    async with session.get(
                                        f"{self.server_url}{endpoint}"
                                    ) as api_resp:
                                        if api_resp.status == 200:
                                            data = await api_resp.json()
                                            self.log_result(
                                                f"API {endpoint}",
                                                "PASS",
                                                f"응답 성공, 데이터 수: {data.get('count', 'N/A')}",
                                            )
                                        else:
                                            self.log_result(
                                                f"API {endpoint}",
                                                "FAIL",
                                                f"HTTP {api_resp.status}",
                                            )
                                except Exception as e:
                                    self.log_result(
                                        f"API {endpoint}", "FAIL", f"요청 실패: {e}"
                                    )
                        else:
                            self.log_result("서버 연결", "FAIL", f"HTTP {resp.status}")

                except aiohttp.ClientConnectorError:
                    self.log_result(
                        "서버 연결", "WARNING", "서버가 실행되지 않음 - API 테스트 스킵"
                    )

        except Exception as e:
            self.log_result("API 엔드포인트 테스트", "FAIL", f"테스트 실패: {e}")

    def generate_test_report(self):
        """테스트 보고서 생성"""
        print("\n" + "=" * 80)
        print("🗄️ Phase 3.1 데이터베이스 통합 테스트 보고서")
        print("=" * 80)

        # 통계 계산
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["status"] == "PASS"])
        failed_tests = len([r for r in self.test_results if r["status"] == "FAIL"])
        warning_tests = len([r for r in self.test_results if r["status"] == "WARNING"])

        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        print("\n📊 테스트 결과 요약:")
        print(f"  총 테스트: {total_tests}개")
        print(f"  ✅ 통과: {passed_tests}개")
        print(f"  ❌ 실패: {failed_tests}개")
        print(f"  ⚠️ 경고: {warning_tests}개")
        print(f"  📈 성공률: {success_rate:.1f}%")

        # 카테고리별 결과
        print("\n📋 카테고리별 결과:")
        categories = {}
        for result in self.test_results:
            category = result["test"].split(" ")[0] if " " in result["test"] else "기타"
            if category not in categories:
                categories[category] = {"pass": 0, "fail": 0, "warning": 0}
            categories[category][result["status"].lower()] += 1

        for category, stats in categories.items():
            total = sum(stats.values())
            rate = (stats["pass"] / total * 100) if total > 0 else 0
            print(f"  {category}: {stats['pass']}/{total} 통과 ({rate:.1f}%)")

        # 실패한 테스트 상세
        if failed_tests > 0:
            print("\n❌ 실패한 테스트 상세:")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    print(f"  - {result['test']}: {result['details']}")

        # 최종 평가
        print("\n🎯 최종 평가:")
        if success_rate >= 90:
            print("  🎊 EXCELLENT: Phase 3.1 데이터베이스 통합이 매우 우수합니다!")
        elif success_rate >= 80:
            print("  ✅ GOOD: Phase 3.1 데이터베이스 통합이 양호합니다.")
        elif success_rate >= 70:
            print("  ⚠️ ACCEPTABLE: 일부 개선이 필요합니다.")
        else:
            print("  ❌ NEEDS_IMPROVEMENT: 상당한 개선이 필요합니다.")

        print("\n" + "=" * 80)

        return success_rate

    async def cleanup_test_db(self):
        """테스트 데이터베이스 정리"""
        try:
            if os.path.exists(self.test_db_path):
                os.remove(self.test_db_path)
                print(f"🗑️ 테스트 데이터베이스 정리 완료: {self.test_db_path}")
        except Exception as e:
            print(f"❌ 테스트 DB 정리 실패: {e}")

    async def run_full_test(self):
        """전체 테스트 실행"""
        print("🗄️ Phase 3.1 데이터베이스 통합 테스트 시작")
        print("=" * 60)

        # 1. 데이터베이스 초기화 테스트
        print("\n📦 데이터베이스 초기화 테스트...")
        await self.test_database_initialization()

        # 2. 측정 데이터 저장/조회 테스트
        print("\n📊 측정 데이터 저장/조회 테스트...")
        await self.test_measurement_storage()

        # 3. 1분 통계 테스트
        print("\n📈 1분 통계 테스트...")
        await self.test_minute_statistics()

        # 4. 알림 이벤트 테스트
        print("\n🚨 알림 이벤트 테스트...")
        await self.test_alert_events()

        # 5. 시스템 로그 테스트
        print("\n📋 시스템 로그 테스트...")
        await self.test_system_logs()

        # 6. 데이터베이스 정리 테스트
        print("\n🧹 데이터베이스 정리 테스트...")
        await self.test_database_cleanup()

        # 7. 데이터베이스 통계 테스트
        print("\n📊 데이터베이스 통계 테스트...")
        await self.test_database_stats()

        # 8. 전력 효율성 분석 테스트
        print("\n⚡ 전력 효율성 분석 테스트...")
        await self.test_power_efficiency()

        # 9. API 엔드포인트 테스트
        print("\n🌐 API 엔드포인트 테스트...")
        await self.test_api_endpoints()

        # 10. 보고서 생성
        success_rate = self.generate_test_report()

        # 11. 테스트 DB 정리
        await self.cleanup_test_db()

        return success_rate


async def main():
    """메인 실행 함수"""
    tester = Phase31DatabaseTester()
    success_rate = await tester.run_full_test()

    # 종료 코드 반환
    if success_rate >= 80:
        sys.exit(0)  # 성공
    else:
        sys.exit(1)  # 실패


if __name__ == "__main__":
    asyncio.run(main())
