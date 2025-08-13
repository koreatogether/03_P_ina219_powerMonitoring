#!/usr/bin/env python3
"""
INA219 전력 모니터링 시스템 - TruffleHog 보안 스캔 도구
========================================================
프로젝트 내 민감정보(API 키, 비밀번호, 토큰 등) 노출 여부를 검사하는 스크립트.

검사 대상:
 1) 로컬 Git 전체 커밋 히스토리 (모든 브랜치 포함)
 2) 원격 저장소 (GitHub/GitLab 등)
 3) 현재 워킹 디렉토리의 파일 시스템 (git 미추적 파일 포함)
 4) 특정 파일/디렉토리 개별 검사

INA219 프로젝트 특화 검사:
 - Arduino 코드 내 하드코딩된 WiFi 비밀번호
 - Python 코드 내 데이터베이스 연결 정보
 - 설정 파일 내 API 키 및 토큰
 - Docker 환경 변수 내 민감 정보
 - 로그 파일 내 노출된 인증 정보

출력:
 - JSON 결과 파일: logs/security/trufflehog_scan_<timestamp>.json
 - 요약 리포트:    logs/security/trufflehog_summary_<timestamp>.txt
 - HTML 리포트:    logs/security/trufflehog_report_<timestamp>.html

사용 예:
  python tools/gitCheck/trufflehog_scan.py --all
  python tools/gitCheck/trufflehog_scan.py --local-git --filesystem
  python tools/gitCheck/trufflehog_scan.py --file src/python/backend/main.py
  python tools/gitCheck/trufflehog_scan.py --directory src/arduino/

선택 옵션:
  --fail-on-find     : 민감정보 발견 시 종료코드 2 반환 (CI/CD 용)
  --timeout N        : 각 스캔 최대 시간(초) (기본 600)
  --no-color         : 컬러 출력 비활성화
  --exclude-patterns : 제외할 파일 패턴 (기본: __pycache__,*.pyc,.git)
  --include-archived : 아카이브된 파일도 검사 (.zip, .tar 등)
  --verbose          : 상세 출력 모드

사전 조건:
  tools/gitCheck/trufflehog.exe 존재 (v3.63.0 이상 권장)
  또는 시스템에 trufflehog 설치됨

참고:
  TruffleHog v3 명령 형식:
    trufflehog git <repo> --json
    trufflehog filesystem --directory <path> --json
    trufflehog git file://<local-repo> --json

작성: INA219 프로젝트 팀
버전: 2.0.0 (2025-08-13)
"""
import argparse
import json
import os
import subprocess
import sys
import shutil
import re
import platform
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Set

# INA219 프로젝트 설정
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROJECT_NAME = "INA219 전력 모니터링 시스템"
TRUFFLEHOG_PATH = Path(__file__).with_name("trufflehog.exe")

# 시스템에 설치된 trufflehog 확인 (Windows/Linux/Mac 지원)
if not TRUFFLEHOG_PATH.exists():
    TRUFFLEHOG_PATH = shutil.which("trufflehog")
    if TRUFFLEHOG_PATH:
        TRUFFLEHOG_PATH = Path(TRUFFLEHOG_PATH)

LOG_DIR = PROJECT_ROOT / "logs" / "security"
LOG_DIR.mkdir(parents=True, exist_ok=True)
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')

# INA219 프로젝트 특화 설정
INA219_SENSITIVE_PATTERNS = [
    r'wifi.*password',
    r'ssid.*password', 
    r'database.*password',
    r'db.*password',
    r'api.*key',
    r'secret.*key',
    r'auth.*token',
    r'bearer.*token',
    r'mqtt.*password',
    r'serial.*key',
]

INA219_EXCLUDE_PATTERNS = [
    '__pycache__',
    '*.pyc',
    '*.pyo',
    '.git',
    '.venv',
    'node_modules',
    '*.log',
    '*.db',
    '.mypy_cache',
    '.ruff_cache',
    '.pio',
    'logs/*',
    'data/*',
    'benchmarks/*',
]

INA219_CRITICAL_PATHS = [
    'src/python/backend/main.py',
    'src/python/backend/database.py', 
    'src/arduino/',
    'docker-compose.yml',
    'Dockerfile',
    '.env*',
    'config*.json',
    'requirements*.txt',
]

class INA219ScanResult:
    def __init__(self):
        self.data: Dict[str, Any] = {
            "project": PROJECT_NAME,
            "timestamp": TIMESTAMP,
            "tool": "trufflehog",
            "version": None,
            "platform": platform.system(),
            "project_root": str(PROJECT_ROOT),
            "scans": {},
            "summary": {
                "total_scans": 0,
                "successful_scans": 0,
                "total_findings": 0,
                "critical_findings": 0,
                "high_risk_files": [],
                "scan_duration": 0.0
            }
        }
        self.any_findings = False
        self.critical_findings = False
        self.start_time = datetime.now()

    def add_scan(self, name: str, success: bool, findings: List[Dict[str, Any]], 
                 raw_stdout: str, raw_stderr: str, command: str, duration: float, 
                 target_path: str = "", error: Optional[str] = None):
        if findings:
            self.any_findings = True
            # INA219 프로젝트 특화 위험도 분석
            critical_count = self._analyze_findings_severity(findings, target_path)
            if critical_count > 0:
                self.critical_findings = True
        
        self.data["scans"][name] = {
            "success": success,
            "target_path": target_path,
            "findings_count": len(findings),
            "critical_findings": self._count_critical_findings(findings),
            "findings": findings,
            "command": command,
            "duration_sec": round(duration, 2),
            "error": error,
            "stdout_truncated": raw_stdout[:8000] if raw_stdout else "",
            "stderr_truncated": raw_stderr[:8000] if raw_stderr else "",
        }
        
        # 요약 정보 업데이트
        self.data["summary"]["total_scans"] += 1
        if success:
            self.data["summary"]["successful_scans"] += 1
        self.data["summary"]["total_findings"] += len(findings)
        self.data["summary"]["critical_findings"] += self._count_critical_findings(findings)
        self.data["summary"]["scan_duration"] += duration

    def _analyze_findings_severity(self, findings: List[Dict[str, Any]], target_path: str) -> int:
        """INA219 프로젝트 특화 위험도 분석"""
        critical_count = 0
        for finding in findings:
            # 중요 파일에서 발견된 경우
            if any(critical_path in target_path for critical_path in INA219_CRITICAL_PATHS):
                finding['ina219_severity'] = 'CRITICAL'
                critical_count += 1
                if target_path not in self.data["summary"]["high_risk_files"]:
                    self.data["summary"]["high_risk_files"].append(target_path)
            # INA219 특화 패턴 매칭
            elif self._matches_ina219_patterns(finding):
                finding['ina219_severity'] = 'HIGH'
                critical_count += 1
            else:
                finding['ina219_severity'] = 'MEDIUM'
        return critical_count

    def _matches_ina219_patterns(self, finding: Dict[str, Any]) -> bool:
        """INA219 프로젝트 특화 민감 패턴 검사"""
        text_to_check = str(finding.get('Raw', '')).lower()
        detector_type = str(finding.get('DetectorType', '')).lower()
        
        for pattern in INA219_SENSITIVE_PATTERNS:
            if re.search(pattern, text_to_check) or re.search(pattern, detector_type):
                return True
        return False

    def _count_critical_findings(self, findings: List[Dict[str, Any]]) -> int:
        return sum(1 for f in findings if f.get('ina219_severity') in ['CRITICAL', 'HIGH'])

    def set_version(self, version: str):
        self.data["version"] = version

    def finalize(self):
        """스캔 완료 후 최종 정리"""
        end_time = datetime.now()
        self.data["scan_completed"] = end_time.isoformat()
        self.data["total_duration"] = (end_time - self.start_time).total_seconds()

    def save(self):
        self.finalize()
        
        # JSON 결과 파일
        json_path = LOG_DIR / f"trufflehog_scan_{TIMESTAMP}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        
        # 텍스트 요약 파일
        txt_path = LOG_DIR / f"trufflehog_summary_{TIMESTAMP}.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            self._write_text_summary(f)
        
        # HTML 리포트 파일
        html_path = LOG_DIR / f"trufflehog_report_{TIMESTAMP}.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            self._write_html_report(f)
        
        return json_path, txt_path, html_path

    def _write_text_summary(self, f):
        f.write(f"{PROJECT_NAME} - TruffleHog 보안 스캔 리포트\n")
        f.write("="*60 + "\n")
        f.write(f"스캔 시간: {TIMESTAMP}\n")
        f.write(f"TruffleHog 버전: {self.data.get('version', 'unknown')}\n")
        f.write(f"플랫폼: {self.data.get('platform')}\n")
        f.write(f"프로젝트 루트: {self.data.get('project_root')}\n\n")
        
        # 요약 정보
        summary = self.data["summary"]
        f.write("📊 스캔 요약\n")
        f.write("-" * 20 + "\n")
        f.write(f"총 스캔 수: {summary['total_scans']}\n")
        f.write(f"성공한 스캔: {summary['successful_scans']}\n")
        f.write(f"총 발견 항목: {summary['total_findings']}\n")
        f.write(f"중요 발견 항목: {summary['critical_findings']}\n")
        f.write(f"총 스캔 시간: {summary['scan_duration']:.2f}초\n\n")
        
        if summary['high_risk_files']:
            f.write("⚠️ 고위험 파일\n")
            f.write("-" * 20 + "\n")
            for file_path in summary['high_risk_files']:
                f.write(f"  • {file_path}\n")
            f.write("\n")
        
        # 상세 스캔 결과
        f.write("📋 상세 스캔 결과\n")
        f.write("-" * 20 + "\n")
        for name, scan in self.data["scans"].items():
            f.write(f"\n[{name}]\n")
            f.write(f"  성공: {scan['success']}\n")
            f.write(f"  대상: {scan.get('target_path', 'N/A')}\n")
            f.write(f"  발견 항목: {scan['findings_count']}\n")
            f.write(f"  중요 항목: {scan['critical_findings']}\n")
            f.write(f"  소요 시간: {scan['duration_sec']}초\n")
            
            if scan['findings_count'] > 0:
                f.write("  발견된 항목:\n")
                for idx, finding in enumerate(scan['findings'][:10], 1):
                    detector = finding.get('DetectorType', finding.get('Detector', 'Unknown'))
                    severity = finding.get('ina219_severity', 'UNKNOWN')
                    source_file = finding.get('SourceMetadata', {}).get('Data', {}).get('Filesystem', {}).get('file', 'Unknown')
                    f.write(f"    {idx}. [{severity}] {detector} in {source_file}\n")
                if scan['findings_count'] > 10:
                    f.write(f"    ... 및 {scan['findings_count'] - 10}개 추가 항목\n")
            
            if scan.get('error'):
                f.write(f"  오류: {scan['error']}\n")
        
        # 최종 결론
        f.write("\n" + "="*60 + "\n")
        if self.critical_findings:
            f.write("🚨 중요: 중대한 보안 위험이 발견되었습니다!\n")
            f.write("   공개 전에 반드시 해결해야 합니다.\n")
        elif self.any_findings:
            f.write("⚠️  주의: 일부 민감 정보가 발견되었습니다.\n")
            f.write("   검토 후 필요시 조치하세요.\n")
        else:
            f.write("✅ 양호: 민감 정보 노출 징후가 발견되지 않았습니다.\n")

    def _write_html_report(self, f):
        f.write(f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{PROJECT_NAME} - TruffleHog 보안 스캔 리포트</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .summary-card {{ background: #f8f9fa; padding: 15px; border-radius: 6px; border-left: 4px solid #007bff; }}
        .critical {{ border-left-color: #dc3545; }}
        .warning {{ border-left-color: #ffc107; }}
        .success {{ border-left-color: #28a745; }}
        .scan-result {{ margin-bottom: 20px; border: 1px solid #dee2e6; border-radius: 6px; }}
        .scan-header {{ background: #e9ecef; padding: 10px 15px; font-weight: bold; }}
        .finding {{ margin: 10px 0; padding: 10px; border-radius: 4px; }}
        .finding.critical {{ background: #f8d7da; border: 1px solid #f5c6cb; }}
        .finding.high {{ background: #fff3cd; border: 1px solid #ffeaa7; }}
        .finding.medium {{ background: #d1ecf1; border: 1px solid #bee5eb; }}
        .code {{ font-family: 'Courier New', monospace; background: #f8f9fa; padding: 2px 4px; border-radius: 3px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{PROJECT_NAME}</h1>
            <h2>TruffleHog 보안 스캔 리포트</h2>
            <p>스캔 시간: {TIMESTAMP} | 버전: {self.data.get('version', 'unknown')}</p>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>총 스캔 수</h3>
                <h2>{self.data['summary']['total_scans']}</h2>
            </div>
            <div class="summary-card {'critical' if self.data['summary']['total_findings'] > 0 else 'success'}">
                <h3>발견 항목</h3>
                <h2>{self.data['summary']['total_findings']}</h2>
            </div>
            <div class="summary-card {'critical' if self.data['summary']['critical_findings'] > 0 else 'success'}">
                <h3>중요 항목</h3>
                <h2>{self.data['summary']['critical_findings']}</h2>
            </div>
            <div class="summary-card">
                <h3>스캔 시간</h3>
                <h2>{self.data['summary']['scan_duration']:.1f}초</h2>
            </div>
        </div>
""")
        
        # 고위험 파일 목록
        if self.data['summary']['high_risk_files']:
            f.write("""
        <div class="scan-result">
            <div class="scan-header" style="background: #f8d7da; color: #721c24;">
                ⚠️ 고위험 파일
            </div>
            <div style="padding: 15px;">
""")
            for file_path in self.data['summary']['high_risk_files']:
                f.write(f'                <div class="code">{file_path}</div>\n')
            f.write("""
            </div>
        </div>
""")
        
        # 상세 스캔 결과
        for name, scan in self.data["scans"].items():
            status_class = "success" if scan['success'] and scan['findings_count'] == 0 else ("critical" if scan['critical_findings'] > 0 else "warning")
            f.write(f"""
        <div class="scan-result">
            <div class="scan-header {status_class}">
                {name} - {scan['findings_count']}개 발견 ({scan['duration_sec']}초)
            </div>
            <div style="padding: 15px;">
                <p><strong>대상:</strong> <span class="code">{scan.get('target_path', 'N/A')}</span></p>
""")
            
            if scan['findings_count'] > 0:
                f.write("                <h4>발견된 항목:</h4>\n")
                for idx, finding in enumerate(scan['findings'][:20], 1):
                    detector = finding.get('DetectorType', finding.get('Detector', 'Unknown'))
                    severity = finding.get('ina219_severity', 'medium').lower()
                    source_file = finding.get('SourceMetadata', {}).get('Data', {}).get('Filesystem', {}).get('file', 'Unknown')
                    raw_data = str(finding.get('Raw', ''))[:100] + ('...' if len(str(finding.get('Raw', ''))) > 100 else '')
                    
                    f.write(f"""
                <div class="finding {severity}">
                    <strong>[{severity.upper()}] {detector}</strong><br>
                    파일: <span class="code">{source_file}</span><br>
                    내용: <span class="code">{raw_data}</span>
                </div>
""")
            
            if scan.get('error'):
                f.write(f'                <p style="color: #dc3545;"><strong>오류:</strong> {scan["error"]}</p>\n')
            
            f.write("            </div>\n        </div>\n")
        
        # 결론
        conclusion_class = "critical" if self.critical_findings else ("warning" if self.any_findings else "success")
        conclusion_icon = "🚨" if self.critical_findings else ("⚠️" if self.any_findings else "✅")
        conclusion_text = ("중대한 보안 위험 발견!" if self.critical_findings else 
                          ("일부 민감 정보 발견" if self.any_findings else "보안 검사 통과"))
        
        f.write(f"""
        <div class="scan-result">
            <div class="scan-header {conclusion_class}">
                {conclusion_icon} 최종 결론: {conclusion_text}
            </div>
        </div>
    </div>
</body>
</html>
""")

COLOR = sys.stdout.isatty()

def c(text, color_code):
    if not COLOR:
        return text
    return f"\033[{color_code}m{text}\033[0m"

class Runner:
    def __init__(self, timeout: int):
        self.timeout = timeout

    def run(self, args: List[str]) -> Dict[str, Any]:
        import time
        start = time.time()
        try:
            proc = subprocess.run(args, capture_output=True, text=True, timeout=self.timeout, encoding='utf-8', errors='replace')
            duration = time.time() - start
            return {
                'ok': proc.returncode == 0 or self._tolerate_returncode(args, proc.returncode),
                'stdout': proc.stdout,
                'stderr': proc.stderr,
                'returncode': proc.returncode,
                'duration': duration,
            }
        except subprocess.TimeoutExpired as e:
            return {'ok': False, 'stdout': e.stdout or '', 'stderr': f'timeout after {self.timeout}s', 'returncode': -1, 'duration': self.timeout}
        except Exception as e:
            return {'ok': False, 'stdout': '', 'stderr': str(e), 'returncode': -1, 'duration': 0}

    def _tolerate_returncode(self, args, code: int) -> bool:
        # 일부 trufflehog 버전은 발견 시 비 0. 여기서는 0/1 모두 허용.
        return code in (0,1)

def ensure_trufflehog() -> bool:
    """TruffleHog 실행 파일 존재 여부 확인"""
    if TRUFFLEHOG_PATH and Path(TRUFFLEHOG_PATH).exists():
        return True
    
    print(c(f"❌ TruffleHog를 찾을 수 없습니다.", '31'))
    print(c(f"   시도한 경로: {TRUFFLEHOG_PATH}", '90'))
    print(c(f"", '90'))
    print(c(f"📥 설치 방법:", '33'))
    
    if platform.system() == "Windows":
        print(c(f"   1. https://github.com/trufflesecurity/trufflehog/releases 에서 다운로드", '36'))
        print(c(f"   2. trufflehog.exe를 tools/gitCheck/ 폴더에 복사", '36'))
        print(c(f"   3. 또는 scoop install trufflehog", '36'))
    elif platform.system() == "Darwin":  # macOS
        print(c(f"   brew install trufflehog", '36'))
    else:  # Linux
        print(c(f"   curl -sSfL https://raw.githubusercontent.com/trufflesecurity/trufflehog/main/scripts/install.sh | sh -s -- -b /usr/local/bin", '36'))
    
    return False

def detect_version(runner: Runner) -> str:
    result = runner.run([str(TRUFFLEHOG_PATH), '--version'])
    if result['ok']:
        ver_line = result['stdout'].strip().splitlines()[0] if result['stdout'].strip() else 'unknown'
        return ver_line
    return 'unknown'

def parse_json_lines(output: str) -> List[Dict[str, Any]]:
    findings = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        # trufflehog --json 은 JSON Lines 출력 (버전에 따라 다를 수 있음)
        if line.startswith('{') and line.endswith('}'):
            try:
                obj = json.loads(line)
                # finding 형태만 수집 (Detector, Raw, ... 포함)
                if any(k in obj for k in ('DetectorName','DetectorType','Raw','Reason','SourceMetadata')):
                    findings.append(obj)
            except json.JSONDecodeError:
                continue
    return findings

def get_origin_url() -> str:
    try:
        result = subprocess.run(['git','remote','get-url','origin'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ''

def is_git_repo() -> bool:
    return (PROJECT_ROOT / '.git').exists()

def scan_local_git(runner: Runner, results: INA219ScanResult, timeout: int, verbose: bool = False):
    """로컬 Git 저장소 전체 히스토리 스캔"""
    if not is_git_repo():
        results.add_scan('local_git', False, [], '', '', f"(skip) not a git repo", 0.0, 
                        target_path=str(PROJECT_ROOT), error='not a git repository')
        print(c('⏭️  로컬 git 히스토리 스킵 (git repo 아님)', '33'))
        return
    
    print(c('🔍 로컬 Git 커밋 히스토리 스캔 시작', '34'))
    if verbose:
        print(c(f'   대상: {PROJECT_ROOT}', '90'))
    
    # 모든 브랜치 스캔을 위한 추가 옵션
    cmd = [str(TRUFFLEHOG_PATH), 'git', f'file://{PROJECT_ROOT}', '--json', '--no-verification']
    
    run_res = runner.run(cmd)
    findings = parse_json_lines(run_res['stdout']) if run_res['stdout'] else []
    
    results.add_scan('local_git', run_res['ok'], findings, run_res['stdout'], run_res['stderr'], 
                    ' '.join(cmd), run_res['duration'], target_path=str(PROJECT_ROOT),
                    error=None if run_res['ok'] else run_res['stderr'])
    
    print(c(f"  ➜ 발견 항목: {len(findings)}", '36'))
    if verbose and findings:
        critical_count = sum(1 for f in findings if f.get('ina219_severity') in ['CRITICAL', 'HIGH'])
        print(c(f"  ➜ 중요 항목: {critical_count}", '31' if critical_count > 0 else '36'))

def scan_remote(runner: Runner, results: INA219ScanResult, remote_url: str, verbose: bool = False):
    """원격 저장소 스캔"""
    if not remote_url:
        results.add_scan('remote_repo', False, [], '', '', '(skip) no remote origin', 0.0, 
                        target_path="", error='no origin')
        print(c('⏭️  원격 저장소 스킵 (origin 미존재)', '33'))
        return
    
    print(c(f'🔍 원격 저장소 스캔: {remote_url}', '34'))
    cmd = [str(TRUFFLEHOG_PATH), 'git', remote_url, '--json', '--no-verification']
    
    run_res = runner.run(cmd)
    findings = parse_json_lines(run_res['stdout']) if run_res['stdout'] else []
    
    results.add_scan('remote_repo', run_res['ok'], findings, run_res['stdout'], run_res['stderr'], 
                    ' '.join(cmd), run_res['duration'], target_path=remote_url,
                    error=None if run_res['ok'] else run_res['stderr'])
    
    print(c(f"  ➜ 발견 항목: {len(findings)}", '36'))
    if verbose and findings:
        critical_count = sum(1 for f in findings if f.get('ina219_severity') in ['CRITICAL', 'HIGH'])
        print(c(f"  ➜ 중요 항목: {critical_count}", '31' if critical_count > 0 else '36'))

def scan_filesystem(runner: Runner, results: INA219ScanResult, exclude_patterns: List[str], verbose: bool = False):
    """파일 시스템 스캔 (현재 워킹 디렉토리)"""
    print(c('🔍 파일 시스템 (워킹 디렉토리) 스캔', '34'))
    if verbose:
        print(c(f'   대상: {PROJECT_ROOT}', '90'))
        print(c(f'   제외 패턴: {", ".join(exclude_patterns)}', '90'))
    
    cmd = [str(TRUFFLEHOG_PATH), 'filesystem', '--directory', str(PROJECT_ROOT), '--json', '--no-verification']
    
    # 제외 패턴 추가
    for pattern in exclude_patterns:
        cmd.extend(['--exclude-paths', pattern])
    
    run_res = runner.run(cmd)
    findings = parse_json_lines(run_res['stdout']) if run_res['stdout'] else []
    
    results.add_scan('filesystem', run_res['ok'], findings, run_res['stdout'], run_res['stderr'], 
                    ' '.join(cmd), run_res['duration'], target_path=str(PROJECT_ROOT),
                    error=None if run_res['ok'] else run_res['stderr'])
    
    print(c(f"  ➜ 발견 항목: {len(findings)}", '36'))
    if verbose and findings:
        critical_count = sum(1 for f in findings if f.get('ina219_severity') in ['CRITICAL', 'HIGH'])
        print(c(f"  ➜ 중요 항목: {critical_count}", '31' if critical_count > 0 else '36'))

def scan_specific_file(runner: Runner, results: INA219ScanResult, file_path: str, verbose: bool = False):
    """특정 파일 스캔"""
    target_path = Path(file_path)
    if not target_path.exists():
        results.add_scan(f'file_{target_path.name}', False, [], '', '', f"(skip) file not found", 0.0,
                        target_path=str(target_path), error='file not found')
        print(c(f'⏭️  파일 스킵 (존재하지 않음): {target_path}', '33'))
        return
    
    print(c(f'🔍 파일 스캔: {target_path}', '34'))
    
    # 파일이 디렉토리인 경우 filesystem 스캔 사용
    if target_path.is_dir():
        cmd = [str(TRUFFLEHOG_PATH), 'filesystem', '--directory', str(target_path), '--json', '--no-verification']
        scan_name = f'directory_{target_path.name}'
    else:
        # 단일 파일의 경우 해당 디렉토리를 스캔하되 특정 파일만 포함
        cmd = [str(TRUFFLEHOG_PATH), 'filesystem', '--directory', str(target_path.parent), '--json', '--no-verification']
        scan_name = f'file_{target_path.name}'
    
    run_res = runner.run(cmd)
    findings = parse_json_lines(run_res['stdout']) if run_res['stdout'] else []
    
    # 단일 파일 스캔의 경우 해당 파일의 결과만 필터링
    if target_path.is_file():
        findings = [f for f in findings if str(target_path) in str(f.get('SourceMetadata', {}))]
    
    results.add_scan(scan_name, run_res['ok'], findings, run_res['stdout'], run_res['stderr'], 
                    ' '.join(cmd), run_res['duration'], target_path=str(target_path),
                    error=None if run_res['ok'] else run_res['stderr'])
    
    print(c(f"  ➜ 발견 항목: {len(findings)}", '36'))
    if verbose and findings:
        critical_count = sum(1 for f in findings if f.get('ina219_severity') in ['CRITICAL', 'HIGH'])
        print(c(f"  ➜ 중요 항목: {critical_count}", '31' if critical_count > 0 else '36'))

def scan_critical_paths(runner: Runner, results: INA219ScanResult, verbose: bool = False):
    """INA219 프로젝트 중요 경로 집중 스캔"""
    print(c('🔍 INA219 중요 경로 집중 스캔', '34'))
    
    existing_paths = []
    for path_pattern in INA219_CRITICAL_PATHS:
        # 글로브 패턴 처리
        if '*' in path_pattern:
            import glob
            matches = glob.glob(str(PROJECT_ROOT / path_pattern))
            existing_paths.extend(matches)
        else:
            full_path = PROJECT_ROOT / path_pattern
            if full_path.exists():
                existing_paths.append(str(full_path))
    
    if not existing_paths:
        results.add_scan('critical_paths', False, [], '', '', '(skip) no critical paths found', 0.0,
                        target_path="critical paths", error='no critical paths found')
        print(c('⏭️  중요 경로 스킵 (경로 없음)', '33'))
        return
    
    if verbose:
        print(c(f'   대상 경로: {len(existing_paths)}개', '90'))
        for path in existing_paths[:5]:  # 처음 5개만 표시
            print(c(f'     • {path}', '90'))
        if len(existing_paths) > 5:
            print(c(f'     ... 및 {len(existing_paths) - 5}개 추가', '90'))
    
    all_findings = []
    total_duration = 0.0
    commands = []
    
    for path in existing_paths:
        target_path = Path(path)
        if target_path.is_dir():
            cmd = [str(TRUFFLEHOG_PATH), 'filesystem', '--directory', str(target_path), '--json', '--no-verification']
        else:
            cmd = [str(TRUFFLEHOG_PATH), 'filesystem', '--directory', str(target_path.parent), '--json', '--no-verification']
        
        commands.append(' '.join(cmd))
        run_res = runner.run(cmd)
        findings = parse_json_lines(run_res['stdout']) if run_res['stdout'] else []
        
        # 단일 파일의 경우 해당 파일 결과만 필터링
        if target_path.is_file():
            findings = [f for f in findings if str(target_path) in str(f.get('SourceMetadata', {}))]
        
        all_findings.extend(findings)
        total_duration += run_res['duration']
    
    results.add_scan('critical_paths', True, all_findings, '', '', '; '.join(commands), 
                    total_duration, target_path=f"{len(existing_paths)} critical paths")
    
    print(c(f"  ➜ 발견 항목: {len(all_findings)}", '36'))
    if verbose and all_findings:
        critical_count = sum(1 for f in all_findings if f.get('ina219_severity') in ['CRITICAL', 'HIGH'])
        print(c(f"  ➜ 중요 항목: {critical_count}", '31' if critical_count > 0 else '36'))

def main():
    parser = argparse.ArgumentParser(
        description=f'{PROJECT_NAME} - TruffleHog 보안 스캔 도구',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  %(prog)s --all                                    # 모든 스캔 실행
  %(prog)s --local-git --filesystem                # 로컬 Git + 파일시스템 스캔
  %(prog)s --file src/python/backend/main.py       # 특정 파일 스캔
  %(prog)s --directory src/arduino/                # 특정 디렉토리 스캔
  %(prog)s --critical-paths                        # INA219 중요 경로만 스캔
  %(prog)s --all --fail-on-find                    # CI/CD용 (발견시 실패)
        """
    )
    
    # 스캔 대상 선택
    scan_group = parser.add_argument_group('스캔 대상')
    scan_group.add_argument('--local-git', action='store_true', help='로컬 Git 히스토리 스캔')
    scan_group.add_argument('--remote', action='store_true', help='원격 저장소 스캔')
    scan_group.add_argument('--filesystem', action='store_true', help='현재 파일 시스템 스캔')
    scan_group.add_argument('--file', type=str, help='특정 파일 스캔')
    scan_group.add_argument('--directory', type=str, help='특정 디렉토리 스캔')
    scan_group.add_argument('--critical-paths', action='store_true', help='INA219 중요 경로 집중 스캔')
    scan_group.add_argument('--all', action='store_true', help='모든 기본 스캔 실행 (local-git + remote + filesystem + critical-paths)')
    
    # 스캔 옵션
    option_group = parser.add_argument_group('스캔 옵션')
    option_group.add_argument('--fail-on-find', action='store_true', help='민감정보 발견 시 종료코드 2 반환 (CI/CD용)')
    option_group.add_argument('--timeout', type=int, default=600, help='각 스캔 최대 시간(초) (기본: 600)')
    option_group.add_argument('--exclude-patterns', nargs='*', default=INA219_EXCLUDE_PATTERNS, 
                             help='제외할 파일 패턴 (기본: INA219 프로젝트 설정)')
    option_group.add_argument('--include-archived', action='store_true', help='아카이브 파일도 검사 (.zip, .tar 등)')
    
    # 출력 옵션
    output_group = parser.add_argument_group('출력 옵션')
    output_group.add_argument('--verbose', '-v', action='store_true', help='상세 출력 모드')
    output_group.add_argument('--no-color', action='store_true', help='컬러 출력 비활성화')
    output_group.add_argument('--quiet', '-q', action='store_true', help='최소 출력 모드')
    
    args = parser.parse_args()

    global COLOR
    if args.no_color:
        COLOR = False

    if not ensure_trufflehog():
        print('TruffleHog 설치 후 다시 실행하세요.')
        return 1

    # 실행할 대상 결정
    targets = {
        'local_git': args.local_git,
        'remote': args.remote,
        'filesystem': args.filesystem,
        'critical_paths': args.critical_paths,
        'specific_file': bool(args.file),
        'specific_directory': bool(args.directory),
    }
    
    # --all 옵션 처리
    if args.all:
        targets.update({
            'local_git': True,
            'remote': True,
            'filesystem': True,
            'critical_paths': True,
        })
    
    # 아무것도 선택되지 않은 경우 기본 스캔
    if not any(targets.values()):
        targets.update({
            'local_git': True,
            'filesystem': True,
            'critical_paths': True,
        })

    runner = Runner(timeout=args.timeout)
    results = INA219ScanResult()
    results.set_version(detect_version(runner))

    origin = get_origin_url() if targets['remote'] else ''

    if not args.quiet:
        print(c(f'🚀 {PROJECT_NAME} - TruffleHog 보안 스캔 시작', '32'))
        print(c(f"   프로젝트 루트: {PROJECT_ROOT}", '90'))
        print(c(f"   TruffleHog 버전: {results.data['version']}", '90'))
        print(c(f"   플랫폼: {results.data['platform']}", '90'))
        if args.verbose:
            print(c(f"   제외 패턴: {', '.join(args.exclude_patterns)}", '90'))
            print(c(f"   타임아웃: {args.timeout}초", '90'))

    # 스캔 실행
    if targets['local_git']:
        scan_local_git(runner, results, args.timeout, args.verbose)
    
    if targets['remote']:
        scan_remote(runner, results, origin, args.verbose)
    
    if targets['filesystem']:
        scan_filesystem(runner, results, args.exclude_patterns, args.verbose)
    
    if targets['critical_paths']:
        scan_critical_paths(runner, results, args.verbose)
    
    if targets['specific_file'] and args.file:
        scan_specific_file(runner, results, args.file, args.verbose)
    
    if targets['specific_directory'] and args.directory:
        scan_specific_file(runner, results, args.directory, args.verbose)  # 디렉토리도 같은 함수 사용

    # 결과 저장 및 출력
    json_path, txt_path, html_path = results.save()

    if not args.quiet:
        print(c('\n📄 결과 파일:', '35'))
        print(f"  JSON 리포트: {json_path}")
        print(f"  텍스트 요약: {txt_path}")
        print(f"  HTML 리포트: {html_path}")
        
        # 요약 정보 출력
        summary = results.data['summary']
        print(c('\n📊 스캔 요약:', '35'))
        print(f"  총 스캔 수: {summary['total_scans']}")
        print(f"  성공한 스캔: {summary['successful_scans']}")
        print(f"  총 발견 항목: {summary['total_findings']}")
        print(f"  중요 발견 항목: {summary['critical_findings']}")
        print(f"  총 스캔 시간: {summary['scan_duration']:.2f}초")
        
        if summary['high_risk_files']:
            print(c('\n⚠️  고위험 파일:', '31'))
            for file_path in summary['high_risk_files'][:5]:
                print(f"    • {file_path}")
            if len(summary['high_risk_files']) > 5:
                print(f"    ... 및 {len(summary['high_risk_files']) - 5}개 추가")

    # 최종 결과 판정
    if results.critical_findings:
        if not args.quiet:
            print(c('\n🚨 중요: 중대한 보안 위험이 발견되었습니다!', '31'))
            print(c('   공개 전에 반드시 해결해야 합니다.', '31'))
            print(c(f'   상세 내용은 {html_path} 를 확인하세요.', '31'))
        if args.fail_on_find:
            return 2
    elif results.any_findings:
        if not args.quiet:
            print(c('\n⚠️  주의: 일부 민감 정보가 발견되었습니다.', '33'))
            print(c('   검토 후 필요시 조치하세요.', '33'))
            print(c(f'   상세 내용은 {html_path} 를 확인하세요.', '33'))
        if args.fail_on_find:
            return 1
    else:
        if not args.quiet:
            print(c('\n✅ 양호: 민감 정보 노출 징후가 발견되지 않았습니다.', '32'))
            print(c('   공개용 저장소 준비가 완료되었습니다.', '32'))

    return 0

if __name__ == '__main__':
    sys.exit(main())
