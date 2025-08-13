#!/usr/bin/env python3
"""
INA219 Power Monitoring Database Manager
Phase 3.1: SQLite Database Integration

기능:
- SQLite 데이터베이스 관리
- 48시간 데이터 저장 및 자동 정리
- 히스토리 데이터 조회 API
- 데이터 백업 및 복구
- 성능 최적화된 인덱스
"""

import asyncio
import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta

import aiosqlite


class PowerDatabase:
    """전력 모니터링 데이터베이스 관리자"""

    def __init__(self, db_path: str = "power_monitoring.db"):
        self.db_path = db_path
        self.data_retention_hours = 48  # 48시간 데이터 보관
        self.logger = logging.getLogger(__name__)

        # 데이터베이스 초기화
        self._init_database()

    def _init_database(self):
        """데이터베이스 테이블 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 전력 측정 데이터 테이블
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS power_measurements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    voltage REAL NOT NULL,
                    current REAL NOT NULL,
                    power REAL NOT NULL,
                    sequence_number INTEGER,
                    sensor_status TEXT,
                    simulation_mode TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # 인덱스 생성
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_power_timestamp ON power_measurements(timestamp)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_power_created_at ON power_measurements(created_at)"
            )

            # 1분 통계 데이터 테이블
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS minute_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    minute_timestamp DATETIME NOT NULL,
                    voltage_min REAL NOT NULL,
                    voltage_max REAL NOT NULL,
                    voltage_avg REAL NOT NULL,
                    current_min REAL NOT NULL,
                    current_max REAL NOT NULL,
                    current_avg REAL NOT NULL,
                    power_min REAL NOT NULL,
                    power_max REAL NOT NULL,
                    power_avg REAL NOT NULL,
                    sample_count INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(minute_timestamp)
                )
            """
            )

            # 인덱스 생성
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_minute_timestamp ON minute_statistics(minute_timestamp)"
            )

            # 알림 이벤트 테이블
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS alert_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    alert_type TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    threshold_value REAL NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT,
                    resolved_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # 인덱스 생성
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_alert_timestamp ON alert_events(timestamp)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_alert_type ON alert_events(alert_type)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_alert_severity ON alert_events(severity)"
            )

            # 시스템 상태 로그 테이블
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    level TEXT NOT NULL,
                    component TEXT NOT NULL,
                    message TEXT NOT NULL,
                    details TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # 인덱스 생성
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_log_timestamp ON system_logs(timestamp)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_log_level ON system_logs(level)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_log_component ON system_logs(component)"
            )

            conn.commit()
            self.logger.info("Database tables initialized successfully")

    async def save_measurement(
        self,
        voltage: float,
        current: float,
        power: float,
        sequence_number: int = None,
        sensor_status: str = "ok",
        simulation_mode: str = "NORMAL",
    ) -> bool:
        """전력 측정 데이터 저장"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO power_measurements
                    (timestamp, voltage, current, power, sequence_number, sensor_status, simulation_mode)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        datetime.now(),
                        voltage,
                        current,
                        power,
                        sequence_number,
                        sensor_status,
                        simulation_mode,
                    ),
                )
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"Failed to save measurement: {e}")
            return False

    async def save_minute_statistics(
        self,
        minute_timestamp: datetime,
        voltage_stats: dict,
        current_stats: dict,
        power_stats: dict,
        sample_count: int,
    ) -> bool:
        """1분 통계 데이터 저장"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO minute_statistics
                    (minute_timestamp, voltage_min, voltage_max, voltage_avg,
                     current_min, current_max, current_avg,
                     power_min, power_max, power_avg, sample_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        minute_timestamp,
                        voltage_stats["min"],
                        voltage_stats["max"],
                        voltage_stats["avg"],
                        current_stats["min"],
                        current_stats["max"],
                        current_stats["avg"],
                        power_stats["min"],
                        power_stats["max"],
                        power_stats["avg"],
                        sample_count,
                    ),
                )
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"Failed to save minute statistics: {e}")
            return False

    async def save_alert_event(
        self,
        alert_type: str,
        metric_name: str,
        metric_value: float,
        threshold_value: float,
        severity: str,
        message: str = None,
    ) -> bool:
        """알림 이벤트 저장"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO alert_events
                    (timestamp, alert_type, metric_name, metric_value,
                     threshold_value, severity, message)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        datetime.now(),
                        alert_type,
                        metric_name,
                        metric_value,
                        threshold_value,
                        severity,
                        message,
                    ),
                )
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"Failed to save alert event: {e}")
            return False

    async def save_system_log(
        self, level: str, component: str, message: str, details: dict = None
    ) -> bool:
        """시스템 로그 저장"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO system_logs
                    (timestamp, level, component, message, details)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        datetime.now(),
                        level,
                        component,
                        message,
                        json.dumps(details) if details else None,
                    ),
                )
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"Failed to save system log: {e}")
            return False

    async def get_recent_measurements(
        self, hours: int = 24, limit: int = 1000
    ) -> list[dict]:
        """최근 측정 데이터 조회"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    """
                    SELECT timestamp, voltage, current, power,
                           sequence_number, sensor_status, simulation_mode
                    FROM power_measurements
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """,
                    (cutoff_time, limit),
                ) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Failed to get recent measurements: {e}")
            return []

    async def get_minute_statistics(self, hours: int = 24) -> list[dict]:
        """1분 통계 데이터 조회"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    """
                    SELECT minute_timestamp, voltage_min, voltage_max, voltage_avg,
                           current_min, current_max, current_avg,
                           power_min, power_max, power_avg, sample_count
                    FROM minute_statistics
                    WHERE minute_timestamp >= ?
                    ORDER BY minute_timestamp DESC
                """,
                    (cutoff_time,),
                ) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Failed to get minute statistics: {e}")
            return []

    async def get_alert_events(
        self, hours: int = 24, severity: str = None
    ) -> list[dict]:
        """알림 이벤트 조회"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            query = """
                SELECT timestamp, alert_type, metric_name, metric_value,
                       threshold_value, severity, message, resolved_at
                FROM alert_events
                WHERE timestamp >= ?
            """
            params = [cutoff_time]

            if severity:
                query += " AND severity = ?"
                params.append(severity)

            query += " ORDER BY timestamp DESC"

            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Failed to get alert events: {e}")
            return []

    async def get_system_logs(
        self, hours: int = 24, level: str = None, component: str = None
    ) -> list[dict]:
        """시스템 로그 조회"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            query = """
                SELECT timestamp, level, component, message, details
                FROM system_logs
                WHERE timestamp >= ?
            """
            params = [cutoff_time]

            if level:
                query += " AND level = ?"
                params.append(level)

            if component:
                query += " AND component = ?"
                params.append(component)

            query += " ORDER BY timestamp DESC"

            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Failed to get system logs: {e}")
            return []

    async def get_database_stats(self) -> dict:
        """데이터베이스 통계 정보"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                stats = {}

                # 각 테이블의 레코드 수
                tables = [
                    "power_measurements",
                    "minute_statistics",
                    "alert_events",
                    "system_logs",
                ]

                for table in tables:
                    async with db.execute(f"SELECT COUNT(*) FROM {table}") as cursor:
                        count = await cursor.fetchone()
                        stats[f"{table}_count"] = count[0]

                # 데이터 범위
                async with db.execute(
                    """
                    SELECT MIN(timestamp) as oldest, MAX(timestamp) as newest
                    FROM power_measurements
                """
                ) as cursor:
                    result = await cursor.fetchone()
                    if result and result[0]:
                        stats["data_range"] = {"oldest": result[0], "newest": result[1]}

                # 파일 크기
                if os.path.exists(self.db_path):
                    stats["file_size_mb"] = os.path.getsize(self.db_path) / (
                        1024 * 1024
                    )

                return stats
        except Exception as e:
            self.logger.error(f"Failed to get database stats: {e}")
            return {}

    async def cleanup_old_data(self) -> dict:
        """48시간 이전 데이터 정리"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=self.data_retention_hours)

            async with aiosqlite.connect(self.db_path) as db:
                cleanup_stats = {}

                # 오래된 측정 데이터 삭제
                async with db.execute(
                    """
                    SELECT COUNT(*) FROM power_measurements WHERE timestamp < ?
                """,
                    (cutoff_time,),
                ) as cursor:
                    old_measurements = await cursor.fetchone()
                    cleanup_stats["measurements_to_delete"] = old_measurements[0]

                await db.execute(
                    """
                    DELETE FROM power_measurements WHERE timestamp < ?
                """,
                    (cutoff_time,),
                )

                # 오래된 1분 통계 삭제
                async with db.execute(
                    """
                    SELECT COUNT(*) FROM minute_statistics WHERE minute_timestamp < ?
                """,
                    (cutoff_time,),
                ) as cursor:
                    old_stats = await cursor.fetchone()
                    cleanup_stats["statistics_to_delete"] = old_stats[0]

                await db.execute(
                    """
                    DELETE FROM minute_statistics WHERE minute_timestamp < ?
                """,
                    (cutoff_time,),
                )

                # 오래된 알림 삭제 (해결된 것만)
                await db.execute(
                    """
                    DELETE FROM alert_events
                    WHERE timestamp < ? AND resolved_at IS NOT NULL
                """,
                    (cutoff_time,),
                )

                # 오래된 시스템 로그 삭제
                await db.execute(
                    """
                    DELETE FROM system_logs WHERE timestamp < ?
                """,
                    (cutoff_time,),
                )

                await db.commit()

                cleanup_stats["cleanup_time"] = datetime.now().isoformat()
                self.logger.info(f"Database cleanup completed: {cleanup_stats}")

                return cleanup_stats
        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")
            return {"error": str(e)}

    async def vacuum_database(self) -> bool:
        """데이터베이스 최적화 (VACUUM)"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("VACUUM")
                await db.commit()
                self.logger.info("Database vacuum completed")
                return True
        except Exception as e:
            self.logger.error(f"Failed to vacuum database: {e}")
            return False

    async def backup_database(self, backup_path: str) -> bool:
        """데이터베이스 백업"""
        try:
            import shutil

            shutil.copy2(self.db_path, backup_path)
            self.logger.info(f"Database backed up to {backup_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to backup database: {e}")
            return False

    async def calculate_power_efficiency(self, hours: int = 24) -> dict:
        """전력 효율성 계산"""
        try:
            measurements = await self.get_recent_measurements(hours=hours)

            if not measurements:
                return {}

            # 효율성 메트릭 계산
            total_energy = sum(m["power"] for m in measurements) / 3600  # Wh
            avg_voltage = sum(m["voltage"] for m in measurements) / len(measurements)
            avg_current = sum(m["current"] for m in measurements) / len(measurements)
            avg_power = sum(m["power"] for m in measurements) / len(measurements)

            # 전력 변동성 (CV - Coefficient of Variation)
            powers = [m["power"] for m in measurements]
            power_std = (sum((p - avg_power) ** 2 for p in powers) / len(powers)) ** 0.5
            power_cv = (power_std / avg_power) * 100 if avg_power > 0 else 0

            return {
                "total_energy_wh": round(total_energy, 3),
                "avg_voltage": round(avg_voltage, 3),
                "avg_current": round(avg_current, 3),
                "avg_power": round(avg_power, 3),
                "power_variability_percent": round(power_cv, 2),
                "sample_count": len(measurements),
                "time_span_hours": hours,
            }
        except Exception as e:
            self.logger.error(f"Failed to calculate power efficiency: {e}")
            return {}


class DatabaseManager:
    """데이터베이스 관리자 싱글톤"""

    _instance = None

    def __new__(cls, db_path: str = "power_monitoring.db"):
        if cls._instance is None:
            cls._instance = PowerDatabase(db_path)
        return cls._instance

    @classmethod
    def get_instance(cls) -> PowerDatabase:
        """데이터베이스 인스턴스 가져오기"""
        if cls._instance is None:
            cls._instance = PowerDatabase()
        return cls._instance


# 자동 정리 태스크
async def auto_cleanup_task():
    """자동 데이터 정리 태스크 (매 시간 실행)"""
    db = DatabaseManager.get_instance()

    while True:
        try:
            # 1시간 대기
            await asyncio.sleep(3600)

            # 데이터 정리 실행
            cleanup_stats = await db.cleanup_old_data()

            # 로그 저장
            await db.save_system_log(
                level="INFO",
                component="database",
                message="Automatic data cleanup completed",
                details=cleanup_stats,
            )

            # 데이터베이스 최적화 (6시간마다)
            current_hour = datetime.now().hour
            if current_hour % 6 == 0:
                await db.vacuum_database()
                await db.save_system_log(
                    level="INFO",
                    component="database",
                    message="Database vacuum completed",
                )

        except Exception as e:
            logging.error(f"Auto cleanup task error: {e}")


if __name__ == "__main__":
    # 테스트 코드
    async def test_database():
        db = DatabaseManager.get_instance()

        # 테스트 데이터 저장
        await db.save_measurement(5.02, 0.245, 1.23, 123, "ok", "NORMAL")

        # 데이터 조회
        measurements = await db.get_recent_measurements(hours=1)
        print(f"Measurements: {len(measurements)}")

        # 통계 정보
        stats = await db.get_database_stats()
        print(f"Database stats: {stats}")

    asyncio.run(test_database())
