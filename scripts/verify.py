#!/usr/bin/env python3
"""
Intelligent ML Studio - Zero-Known-Defect Release Verification Gate.

Executes sequential multi-stage validation across:
1. Python Environment & Dependency Integrity
2. Python Syntax Compilation
3. Backend Test Suite (Pytest Unit + Invariants + Gate + Security)
4. Storage & Directory Traversal Security Gate
5. Live Measurement Evidence Pack Generation
6. Frontend TypeScript Typecheck (tsc --noEmit)
7. Frontend Vitest Test Suite
8. Frontend Production Bundle (Vite)
9. Release Packaging Hygiene & Artifact Containment

Outputs an immutable, measurement-derived release certificate JSON to evidence/release_certificate.json.
"""

import sys
import os
import re
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime, timezone

# Ensure UTF-8 output on all platforms including Windows CP1252 consoles
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "apps" / "frontend"
BACKEND_DIR = ROOT_DIR / "apps" / "backend"
EVIDENCE_DIR = ROOT_DIR / "evidence"


def get_git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(ROOT_DIR), text=True).strip()
    except Exception:
        return "unversioned"


def run_step(step_name: str, cmd: list[str], cwd: Path) -> tuple[bool, str, float]:
    print(f"\n[{step_name}] Running: {' '.join(cmd)}", flush=True)
    start_time = time.time()
    
    is_win = (sys.platform == "win32")
    is_npm = cmd[0] in ["npm", "npx"]
    
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["ENV"] = "testing"
        
        if is_win and is_npm:
            exec_args = " ".join(cmd)
            use_shell = True
        else:
            exec_args = cmd
            use_shell = False
        
        proc = subprocess.Popen(
            exec_args,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            shell=use_shell
        )
        
        output_lines = []
        for line in iter(proc.stdout.readline, ""):
            output_lines.append(line)
            lower = line.lower()
            if any(k in lower for k in ["passed", "error", "failed", "building", "built", "%", "saved", "ok", "verified"]):
                print(f"  > {line.strip()}", flush=True)
                
        proc.stdout.close()
        proc.wait()
        
        duration = time.time() - start_time
        success = (proc.returncode == 0)
        full_output = "".join(output_lines).strip()
        
        if success:
            print(f"[{step_name}] PASSED ({duration:.2f}s)", flush=True)
        else:
            print(f"[{step_name}] FAILED (exit code {proc.returncode}, {duration:.2f}s)", flush=True)
            print("-" * 40 + " OUTPUT " + "-" * 40, flush=True)
            clean_out = full_output.encode('ascii', errors='replace').decode('ascii')
            print(clean_out[:3000] + ("\n... [truncated]" if len(clean_out) > 3000 else ""), flush=True)
            print("-" * 88, flush=True)
            
        return success, full_output, duration
    except Exception as e:
        duration = time.time() - start_time
        print(f"[{step_name}] ERROR: {e}", flush=True)
        return False, str(e), duration


def main():
    print("=" * 80, flush=True)
    print(" INTELLIGENT ML STUDIO — ZERO-KNOWN-DEFECT RELEASE VERIFICATION GATE", flush=True)
    print("=" * 80, flush=True)
    
    stages_record = {}
    results = []
    
    # 1. Python Environment Check
    s1_success, s1_out, s1_dur = run_step(
        "1. Dependency & Environment Integrity",
        [sys.executable, "-c", "import fastapi, sqlalchemy, pydantic, jose, sklearn, shap, boto3, pyarrow, openpyxl; print('All core runtime & worker dependencies verified.')"],
        ROOT_DIR
    )
    results.append(("1. Dependency Integrity", s1_success, s1_dur))
    stages_record["dependencies"] = {"status": "PASSED" if s1_success else "FAILED", "duration_s": round(s1_dur, 2)}
    if not s1_success:
        sys.exit(1)

    # 2. Syntax & Compilation Gate
    s2_success, s2_out, s2_dur = run_step(
        "2. Python Bytecode Compilation",
        [sys.executable, "-m", "compileall", "-q", "apps/backend/app"],
        ROOT_DIR
    )
    results.append(("2. Bytecode Compilation", s2_success, s2_dur))
    stages_record["compilation"] = {"status": "PASSED" if s2_success else "FAILED", "duration_s": round(s2_dur, 2)}
    if not s2_success:
        sys.exit(1)

    # 3. Backend Test Suite (Pytest)
    s3_success, s3_out, s3_dur = run_step(
        "3. Backend Pytest Suite",
        [sys.executable, "-m", "pytest", "apps/backend/tests", "-q"],
        ROOT_DIR
    )
    passed_match = re.search(r"(\d+)\s+passed", s3_out)
    passed_count = int(passed_match.group(1)) if passed_match else 0
    failed_match = re.search(r"(\d+)\s+failed", s3_out)
    failed_count = int(failed_match.group(1)) if failed_match else 0
    count_label = f" ({passed_count} Passed)" if passed_count else ""
    results.append((f"3. Backend Test Suite{count_label}", s3_success, s3_dur))
    stages_record["backend_tests"] = {
        "status": "PASSED" if s3_success else "FAILED",
        "passed": passed_count,
        "failed": failed_count,
        "duration_s": round(s3_dur, 2)
    }
    if not s3_success:
        sys.exit(1)

    # 4. Storage & Traversal Security Invariant Gate
    s4_success, s4_out, s4_dur = run_step(
        "4. Storage Security & Containment Invariants",
        [sys.executable, "-m", "pytest", "apps/backend/tests/test_storage_security.py", "-q"],
        ROOT_DIR
    )
    results.append(("4. Storage Containment Gate", s4_success, s4_dur))
    stages_record["storage_security"] = {"status": "PASSED" if s4_success else "FAILED", "duration_s": round(s4_dur, 2)}
    if not s4_success:
        sys.exit(1)

    # 5. Live Measurement Evidence Pack Generation
    s5_success, s5_out, s5_dur = run_step(
        "5. Live Measurement Evidence Generation",
        [sys.executable, "scripts/generate_evidence_pack.py"],
        ROOT_DIR
    )
    results.append(("5. Evidence Pack Generation", s5_success, s5_dur))
    stages_record["evidence_generation"] = {"status": "PASSED" if s5_success else "FAILED", "duration_s": round(s5_dur, 2)}
    if not s5_success:
        sys.exit(1)

    # 6. Frontend TypeScript Typecheck
    s6_success, s6_out, s6_dur = run_step(
        "6. Frontend Typecheck (tsc)",
        ["npm", "run", "typecheck"],
        FRONTEND_DIR
    )
    results.append(("6. Frontend Typecheck", s6_success, s6_dur))
    stages_record["frontend_typecheck"] = {"status": "PASSED" if s6_success else "FAILED", "duration_s": round(s6_dur, 2)}
    if not s6_success:
        sys.exit(1)

    # 7. Frontend Vitest Tests
    s7_success, s7_out, s7_dur = run_step(
        "7. Frontend Unit & Component Tests",
        ["npm", "test"],
        FRONTEND_DIR
    )
    results.append(("7. Frontend Tests (Vitest)", s7_success, s7_dur))
    stages_record["frontend_tests"] = {"status": "PASSED" if s7_success else "FAILED", "duration_s": round(s7_dur, 2)}
    if not s7_success:
        sys.exit(1)

    # 8. Frontend Production Bundle Build
    s8_success, s8_out, s8_dur = run_step(
        "8. Frontend Production Bundle (Vite)",
        ["npm", "run", "build"],
        FRONTEND_DIR
    )
    results.append(("8. Frontend Production Build", s8_success, s8_dur))
    stages_record["frontend_build"] = {"status": "PASSED" if s8_success else "FAILED", "duration_s": round(s8_dur, 2)}
    if not s8_success:
        sys.exit(1)

    # 9. Release Packaging Hygiene Validation
    s9_success, s9_out, s9_dur = run_step(
        "9. Release Packaging Hygiene & Clean Archive Gate",
        [sys.executable, "scripts/package_release.py", "--verify-clean"],
        ROOT_DIR
    )
    results.append(("9. Clean Packaging Gate", s9_success, s9_dur))
    stages_record["release_hygiene"] = {"status": "PASSED" if s9_success else "FAILED", "duration_s": round(s9_dur, 2)}
    if not s9_success:
        sys.exit(1)

    # Output Scorecard
    print("\n" + "=" * 80, flush=True)
    print(" ZERO-KNOWN-DEFECT VERIFICATION SCORECARD", flush=True)
    print("=" * 80, flush=True)
    print(f"{'Verification Stage':<48} | {'Duration':<10} | {'Status':<10}", flush=True)
    print("-" * 80, flush=True)
    
    all_passed = True
    total_time = 0.0
    for name, success, dur in results:
        status_str = "PASSED" if success else "FAILED"
        print(f"{name:<48} | {dur:>8.2f}s | {status_str:<10}", flush=True)
        if not success:
            all_passed = False
        total_time += dur
        
    print("-" * 80, flush=True)
    print(f"{'Total Verification Duration':<48} | {total_time:>8.2f}s |", flush=True)
    print("=" * 80, flush=True)
    
    # Save Immutable Verification Certificate
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    certificate = {
        "platform": "Intelligent ML Studio",
        "version": "1.0.0",
        "git_commit": get_git_commit(),
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "total_duration_seconds": round(total_time, 2),
        "stages": stages_record,
        "release_verdict": "ZERO_KNOWN_DEFECT_CERTIFIED" if all_passed else "RELEASE_BLOCKED"
    }
    
    cert_path = EVIDENCE_DIR / "release_certificate.json"
    with open(cert_path, "w", encoding="utf-8") as f:
        json.dump(certificate, f, indent=2)
    print(f"\n[CERTIFICATE] Saved verified release certificate to: {cert_path.relative_to(ROOT_DIR)}")

    if all_passed:
        print("\n>>> ALL 9 RELEASE GATES PASSED: ZERO-KNOWN-DEFECT RELEASE CERTIFIED <<<\n", flush=True)
        sys.exit(0)
    else:
        print("\n>>> VERIFICATION FAILED: RELEASE BLOCKED <<<\n", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
