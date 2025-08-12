#!/usr/bin/env python3
"""
INA219 Power Monitoring System - All Checks Runner
모든 검사 도구를 순차적으로 실행하는 통합 스크립트
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_tool(tool_name, tool_path, description):
    """개별 도구 실행"""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"{'='*60}")
    
    try:
        start_time = datetime.now()
        result = subprocess.run(
            [sys.executable, tool_path],
            cwd=tool_path.parent.parent,
            check=False
        )
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if result.returncode == 0:
            print(f"\n✅ {tool_name} 완료 (소요시간: {duration:.1f}초)")
            return True
        else:
            print(f"\n❌ {tool_name} 실패 (종료코드: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"\n❌ {tool_name} 실행 오류: {e}")
        return False


def main():
    """메인 함수"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    print("🚀 INA219 Power Monitoring - 전체 검사 시작")
    print(f"프로젝트 경로: {project_root}")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 실행할 도구들 정의
    tools = [
        ("코드 품질 검사", script_dir / "code_quality_checker.py", "Code Quality Check"),
        ("빌드 및 테스트", script_dir / "build_and_test.py", "Build and Test"),
        ("성능 분석", script_dir / "performance_analyzer.py", "Performance Analysis")
    ]
    
    # 각 도구 실행
    results = {}
    total_start_time = datetime.now()
    
    for tool_name, tool_path, description in tools:
        if tool_path.exists():
            success = run_tool(tool_name, tool_path, description)
            results[tool_name] = success
        else:
            print(f"\n⚠️  {tool_name} 파일을 찾을 수 없습니다: {tool_path}")
            results[tool_name] = False
    
    # 최종 결과 요약
    total_end_time = datetime.now()
    total_duration = (total_end_time - total_start_time).total_seconds()
    
    print(f"\n{'='*60}")
    print("📊 전체 검사 결과 요약")
    print(f"{'='*60}")
    
    success_count = sum(1 for success in results.values() if success)
    total_count = len(results)
    
    for tool_name, success in results.items():
        status_icon = "✅" if success else "❌"
        print(f"  {status_icon} {tool_name}")
    
    print(f"\n🎯 성공률: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
    print(f"⏱️  총 소요시간: {total_duration:.1f}초")
    print(f"🏁 완료 시간: {total_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 로그 디렉토리 안내
    logs_dir = project_root / "logs"
    if logs_dir.exists():
        print(f"\n📁 상세 로그는 다음 디렉토리에서 확인하세요:")
        print(f"   {logs_dir}")
        
        # 각 로그 디렉토리 확인
        for subdir in ["quality", "build_test", "performance"]:
            log_subdir = logs_dir / subdir
            if log_subdir.exists():
                log_files = list(log_subdir.glob("*.txt")) + list(log_subdir.glob("*.json"))
                if log_files:
                    latest_log = max(log_files, key=lambda f: f.stat().st_mtime)
                    print(f"   📄 {subdir}: {latest_log.name}")
    
    # 다음 단계 안내
    if success_count == total_count:
        print(f"\n🎉 모든 검사가 성공적으로 완료되었습니다!")
        print("💡 다음 단계:")
        print("   1. 대시보드 실행: python -m uv run python src/python/dashboard/app.py")
        print("   2. Arduino 코드 업로드: pio run -t upload")
        print("   3. 실시간 모니터링 시작")
    else:
        print(f"\n⚠️  일부 검사에서 문제가 발견되었습니다.")
        print("💡 문제 해결:")
        print("   1. 위의 로그 파일들을 확인하세요")
        print("   2. 개별 도구를 다시 실행해보세요")
        print("   3. 의존성이 모두 설치되었는지 확인하세요")
    
    # 종료 코드 반환
    sys.exit(0 if success_count == total_count else 1)


if __name__ == "__main__":
    main()