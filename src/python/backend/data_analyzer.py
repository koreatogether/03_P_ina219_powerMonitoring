#!/usr/bin/env python3
"""
INA219 Power Monitoring System - Data Analyzer
Phase 4.1: 이동평균 + 이상치 탐지 시스템

기능:
- 이동평균 계산 (1분, 5분, 15분)
- 이상치 탐지 (Z-score, IQR 방법)
- 실시간 통계 분석
- 데이터 품질 평가
"""

import sqlite3
import statistics
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import numpy as np


@dataclass
class AnalysisResult:
    """분석 결과 데이터 클래스"""

    timestamp: datetime
    value: float
    moving_avg_1m: float
    moving_avg_5m: float
    moving_avg_15m: float
    is_outlier: bool
    outlier_score: float
    outlier_method: str
    confidence: float


@dataclass
class OutlierStats:
    """이상치 통계 데이터 클래스"""

    total_samples: int
    outlier_count: int
    outlier_rate: float
    last_outlier_time: Optional[datetime]
    severity_distribution: dict[str, int]  # mild, moderate, severe


class MovingAverageCalculator:
    """이동평균 계산기"""

    def __init__(self, window_sizes: dict[str, int] = None):
        if window_sizes is None:
            window_sizes = {
                "1m": 60,  # 1분 = 60초 (1초 간격 데이터)
                "5m": 300,  # 5분 = 300초
                "15m": 900,  # 15분 = 900초
            }

        self.window_sizes = window_sizes
        self.data_buffers = {
            "voltage": {key: deque(maxlen=size) for key, size in window_sizes.items()},
            "current": {key: deque(maxlen=size) for key, size in window_sizes.items()},
            "power": {key: deque(maxlen=size) for key, size in window_sizes.items()},
        }

    def add_data(self, voltage: float, current: float, power: float):
        """새 데이터 추가"""
        for metric in ["voltage", "current", "power"]:
            value = locals()[metric]
            for window in self.data_buffers[metric]:
                self.data_buffers[metric][window].append(value)

    def get_moving_averages(self, metric: str) -> dict[str, float]:
        """지정된 메트릭의 이동평균 계산"""
        if metric not in self.data_buffers:
            return {}

        averages = {}
        for window, buffer in self.data_buffers[metric].items():
            if len(buffer) > 0:
                averages[window] = statistics.mean(buffer)
            else:
                averages[window] = 0.0

        return averages

    def get_all_moving_averages(self) -> dict[str, dict[str, float]]:
        """모든 메트릭의 이동평균 계산"""
        return {
            metric: self.get_moving_averages(metric)
            for metric in self.data_buffers.keys()
        }


class OutlierDetector:
    """이상치 탐지기"""

    def __init__(
        self,
        z_threshold: float = 2.5,
        iqr_multiplier: float = 1.5,
        min_samples: int = 30,
    ):
        self.z_threshold = z_threshold
        self.iqr_multiplier = iqr_multiplier
        self.min_samples = min_samples

        # 데이터 버퍼 (최근 1000개 데이터 유지)
        self.data_history = {
            "voltage": deque(maxlen=1000),
            "current": deque(maxlen=1000),
            "power": deque(maxlen=1000),
        }

    def add_data(self, voltage: float, current: float, power: float):
        """새 데이터 추가"""
        self.data_history["voltage"].append(voltage)
        self.data_history["current"].append(current)
        self.data_history["power"].append(power)

    def detect_outliers_zscore(self, metric: str, value: float) -> tuple[bool, float]:
        """Z-score 방법으로 이상치 탐지"""
        if metric not in self.data_history:
            return False, 0.0

        data = list(self.data_history[metric])
        if len(data) < self.min_samples:
            return False, 0.0

        try:
            mean = statistics.mean(data)
            stdev = statistics.stdev(data)

            if stdev == 0:
                return False, 0.0

            z_score = abs((value - mean) / stdev)
            is_outlier = z_score > self.z_threshold

            return is_outlier, z_score

        except Exception:
            return False, 0.0

    def detect_outliers_iqr(self, metric: str, value: float) -> tuple[bool, float]:
        """IQR 방법으로 이상치 탐지"""
        if metric not in self.data_history:
            return False, 0.0

        data = list(self.data_history[metric])
        if len(data) < self.min_samples:
            return False, 0.0

        try:
            data_sorted = sorted(data)
            n = len(data_sorted)

            q1_idx = n // 4
            q3_idx = 3 * n // 4

            q1 = data_sorted[q1_idx]
            q3 = data_sorted[q3_idx]
            iqr = q3 - q1

            if iqr == 0:
                return False, 0.0

            lower_bound = q1 - self.iqr_multiplier * iqr
            upper_bound = q3 + self.iqr_multiplier * iqr

            is_outlier = value < lower_bound or value > upper_bound

            # IQR 점수 계산 (경계로부터의 거리)
            if value < lower_bound:
                iqr_score = (lower_bound - value) / iqr
            elif value > upper_bound:
                iqr_score = (value - upper_bound) / iqr
            else:
                iqr_score = 0.0

            return is_outlier, iqr_score

        except Exception:
            return False, 0.0

    def detect_outlier(self, metric: str, value: float) -> dict[str, Any]:
        """종합 이상치 탐지"""
        # Z-score 방법
        z_outlier, z_score = self.detect_outliers_zscore(metric, value)

        # IQR 방법
        iqr_outlier, iqr_score = self.detect_outliers_iqr(metric, value)

        # 두 방법 중 하나라도 이상치로 판단하면 이상치로 분류
        is_outlier = z_outlier or iqr_outlier

        # 더 높은 점수를 사용
        if z_score > iqr_score:
            primary_method = "z-score"
            primary_score = z_score
        else:
            primary_method = "iqr"
            primary_score = iqr_score

        # 신뢰도 계산 (데이터 샘플 수 기반)
        sample_count = len(self.data_history[metric])
        confidence = min(sample_count / 100.0, 1.0)  # 100개 샘플에서 100% 신뢰도

        # 심각도 분류
        if primary_score > 4.0:
            severity = "severe"
        elif primary_score > 2.5:
            severity = "moderate"
        else:
            severity = "mild"

        return {
            "is_outlier": is_outlier,
            "method": primary_method,
            "score": primary_score,
            "z_score": z_score,
            "iqr_score": iqr_score,
            "confidence": confidence,
            "severity": severity,
            "sample_count": sample_count,
        }


class DataAnalyzer:
    """데이터 분석기 메인 클래스"""

    def __init__(self, db_path: str = "power_monitoring.db"):
        self.db_path = db_path
        self.moving_avg_calc = MovingAverageCalculator()
        self.outlier_detector = OutlierDetector()

        # 이상치 통계
        self.outlier_stats = {
            "voltage": OutlierStats(
                0, 0, 0.0, None, {"mild": 0, "moderate": 0, "severe": 0}
            ),
            "current": OutlierStats(
                0, 0, 0.0, None, {"mild": 0, "moderate": 0, "severe": 0}
            ),
            "power": OutlierStats(
                0, 0, 0.0, None, {"mild": 0, "moderate": 0, "severe": 0}
            ),
        }

        # 최근 분석 결과 (차트 표시용)
        self.recent_results = deque(maxlen=1000)

    def analyze_data_point(
        self, voltage: float, current: float, power: float
    ) -> dict[str, Any]:
        """단일 데이터 포인트 분석"""
        timestamp = datetime.now()

        # 이동평균 계산기에 데이터 추가
        self.moving_avg_calc.add_data(voltage, current, power)

        # 이상치 탐지기에 데이터 추가
        self.outlier_detector.add_data(voltage, current, power)

        # 이동평균 계산
        moving_averages = self.moving_avg_calc.get_all_moving_averages()

        # 각 메트릭별 이상치 탐지
        analysis_results = {}

        for metric, value in [
            ("voltage", voltage),
            ("current", current),
            ("power", power),
        ]:
            outlier_result = self.outlier_detector.detect_outlier(metric, value)

            # 통계 업데이트
            stats = self.outlier_stats[metric]
            stats.total_samples += 1

            if outlier_result["is_outlier"]:
                stats.outlier_count += 1
                stats.last_outlier_time = timestamp
                stats.severity_distribution[outlier_result["severity"]] += 1

            stats.outlier_rate = (
                stats.outlier_count / stats.total_samples
                if stats.total_samples > 0
                else 0.0
            )

            # 분석 결과 구성
            analysis_results[metric] = {
                "value": value,
                "moving_avg": moving_averages[metric],
                "outlier": outlier_result,
                "stats": {
                    "total_samples": stats.total_samples,
                    "outlier_count": stats.outlier_count,
                    "outlier_rate": stats.outlier_rate,
                    "last_outlier_time": (
                        stats.last_outlier_time.isoformat()
                        if stats.last_outlier_time
                        else None
                    ),
                },
            }

        # 전체 분석 결과
        overall_result = {
            "timestamp": timestamp.isoformat(),
            "metrics": analysis_results,
            "has_any_outlier": any(
                analysis_results[m]["outlier"]["is_outlier"] for m in analysis_results
            ),
            "outlier_count": sum(
                1
                for m in analysis_results
                if analysis_results[m]["outlier"]["is_outlier"]
            ),
            "confidence": statistics.mean(
                [analysis_results[m]["outlier"]["confidence"] for m in analysis_results]
            ),
        }

        # 최근 결과에 추가
        self.recent_results.append(overall_result)

        return overall_result

    def get_outlier_summary(self) -> dict[str, Any]:
        """이상치 요약 통계"""
        summary = {}

        for metric, stats in self.outlier_stats.items():
            summary[metric] = {
                "total_samples": stats.total_samples,
                "outlier_count": stats.outlier_count,
                "outlier_rate": round(stats.outlier_rate * 100, 2),  # 백분율
                "last_outlier_time": (
                    stats.last_outlier_time.isoformat()
                    if stats.last_outlier_time
                    else None
                ),
                "severity_distribution": stats.severity_distribution.copy(),
            }

        # 전체 통계
        total_samples = sum(
            stats.total_samples for stats in self.outlier_stats.values()
        )
        total_outliers = sum(
            stats.outlier_count for stats in self.outlier_stats.values()
        )

        summary["overall"] = {
            "total_samples": total_samples,
            "total_outliers": total_outliers,
            "overall_outlier_rate": round(
                (total_outliers / total_samples * 100) if total_samples > 0 else 0, 2
            ),
            "metrics_with_outliers": sum(
                1 for stats in self.outlier_stats.values() if stats.outlier_count > 0
            ),
        }

        return summary

    def get_recent_outliers(self, limit: int = 10) -> list[dict[str, Any]]:
        """최근 이상치 목록"""
        outliers = []

        for result in reversed(self.recent_results):
            if result["has_any_outlier"]:
                outlier_metrics = []
                for metric, data in result["metrics"].items():
                    if data["outlier"]["is_outlier"]:
                        outlier_metrics.append(
                            {
                                "metric": metric,
                                "value": data["value"],
                                "score": data["outlier"]["score"],
                                "severity": data["outlier"]["severity"],
                                "method": data["outlier"]["method"],
                            }
                        )

                outliers.append(
                    {
                        "timestamp": result["timestamp"],
                        "outlier_count": result["outlier_count"],
                        "confidence": result["confidence"],
                        "metrics": outlier_metrics,
                    }
                )

                if len(outliers) >= limit:
                    break

        return outliers

    def save_analysis_to_db(self, analysis_result: dict[str, Any]):
        """분석 결과를 데이터베이스에 저장"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 분석 결과 테이블 생성 (없으면)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    value REAL NOT NULL,
                    moving_avg_1m REAL,
                    moving_avg_5m REAL,
                    moving_avg_15m REAL,
                    is_outlier BOOLEAN NOT NULL,
                    outlier_score REAL,
                    outlier_method TEXT,
                    severity TEXT,
                    confidence REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # 각 메트릭별 결과 저장
            for metric, data in analysis_result["metrics"].items():
                cursor.execute(
                    """
                    INSERT INTO analysis_results
                    (timestamp, metric, value, moving_avg_1m, moving_avg_5m, moving_avg_15m,
                     is_outlier, outlier_score, outlier_method, severity, confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        analysis_result["timestamp"],
                        metric,
                        data["value"],
                        data["moving_avg"].get("1m", 0),
                        data["moving_avg"].get("5m", 0),
                        data["moving_avg"].get("15m", 0),
                        data["outlier"]["is_outlier"],
                        data["outlier"]["score"],
                        data["outlier"]["method"],
                        data["outlier"]["severity"],
                        data["outlier"]["confidence"],
                    ),
                )

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"Error saving analysis to database: {e}")


# 테스트 및 데모 함수
def demo_data_analyzer():
    """데이터 분석기 데모"""
    print("🔍 Data Analyzer Demo")
    print("=" * 40)

    analyzer = DataAnalyzer()

    # 정상 데이터 시뮬레이션
    print("📊 Adding normal data...")
    for i in range(50):
        voltage = 5.0 + np.random.normal(0, 0.02)  # 정상 범위
        current = 0.25 + np.random.normal(0, 0.01)
        power = voltage * current

        result = analyzer.analyze_data_point(voltage, current, power)

        if i % 10 == 0:
            print(f"  Sample {i+1}: V={voltage:.3f}V, A={current:.3f}A, W={power:.3f}W")

    # 이상치 데이터 추가
    print("\n⚠️ Adding outlier data...")
    outlier_data = [
        (6.5, 0.25, 1.625),  # 전압 이상치
        (5.0, 0.8, 4.0),  # 전류 이상치
        (5.0, 0.25, 2.5),  # 전력 이상치 (계산 불일치)
    ]

    for voltage, current, power in outlier_data:
        result = analyzer.analyze_data_point(voltage, current, power)
        print(f"  Outlier: V={voltage:.3f}V, A={current:.3f}A, W={power:.3f}W")

        if result["has_any_outlier"]:
            print(f"    🚨 Detected {result['outlier_count']} outlier(s)")

    # 통계 요약
    print("\n📈 Analysis Summary:")
    summary = analyzer.get_outlier_summary()

    for metric, stats in summary.items():
        if metric != "overall":
            print(f"  {metric.capitalize()}:")
            print(f"    Samples: {stats['total_samples']}")
            print(f"    Outliers: {stats['outlier_count']} ({stats['outlier_rate']}%)")

    print(f"\n🎯 Overall outlier rate: {summary['overall']['overall_outlier_rate']}%")

    # 최근 이상치
    recent_outliers = analyzer.get_recent_outliers(5)
    if recent_outliers:
        print(f"\n🚨 Recent outliers ({len(recent_outliers)}):")
        for outlier in recent_outliers:
            print(f"  {outlier['timestamp']}: {outlier['outlier_count']} outlier(s)")


if __name__ == "__main__":
    demo_data_analyzer()
