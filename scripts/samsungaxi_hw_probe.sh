#!/usr/bin/env bash
# SAMSUNGAXI project PC hardware diagnostic (read-only, no global settings).
# Windows host via PowerShell CIM + WSL2 Ubuntu visible resources + WSLg render.
set -Eeuo pipefail

usage() {
  cat <<'USAGE'
Usage: bash samsungaxi_hw_probe.sh [--output-dir DIRECTORY] [--compare-gpu] [--gazebo-stats] [--self-test]
  --output-dir DIR  Report directory (default: <repo>/logs/hardware/<UTC timestamp>)
  --compare-gpu     Probe optional WSLg GPU adapter candidates, no persistent changes
  --gazebo-stats    Attempt one bounded Gazebo world stats sample (optional)
  --self-test       Check Python availability and syntax entrypoint; no hardware accessed
Read-only: does not install drivers, change .wslconfig, set GPU/CPU limits, or stop Gazebo.
Reports contain CPU/GPU model, RAM size and drivers; review before sharing publicly.
USAGE
}
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="$ROOT/logs/hardware/$(date -u +%Y%m%dT%H%M%SZ)"
COMPARE_GPU=0
GAZEBO_STATS=0
SELF_TEST=0
while (( $# )); do
  case "$1" in
    --output-dir) (( $# >= 2 )) || { echo 'ERROR: --output-dir requires path' >&2; exit 2; }; OUTPUT_DIR="$2"; shift 2 ;;
    --compare-gpu) COMPARE_GPU=1; shift ;;
    --gazebo-stats) GAZEBO_STATS=1; shift ;;
    --self-test) SELF_TEST=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown option $1" >&2; usage; exit 2 ;;
  esac
done
command -v python3 >/dev/null || { echo 'BLOCKED: python3 required' >&2; exit 2; }
if (( SELF_TEST )); then echo 'SAMSUNGAXI_HARDWARE_PROBE_SELF_TEST_PASS_NO_HARDWARE'; exit 0; fi
mkdir -p -- "$OUTPUT_DIR"
python3 - "$OUTPUT_DIR" "$COMPARE_GPU" "$GAZEBO_STATS" <<'PY'
import base64
import datetime
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

outdir = Path(sys.argv[1]).resolve()
compare_gpu = sys.argv[2] == '1'
gazebo_stats = sys.argv[3] == '1'


def run(argv, *, timeout=8, env=None, limit=8000):
    """Run bounded read-only diagnostics and truncate long outputs."""
    try:
        r = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           text=True, errors='replace', env=env, timeout=timeout, check=False)
        return {'status': 'ok' if r.returncode == 0 else 'error', 'exit_code': r.returncode,
                'stdout': r.stdout[:limit].strip(), 'stderr': r.stderr[:800].strip()}
    except FileNotFoundError:
        return {'status': 'unavailable', 'reason': 'command not installed'}
    except subprocess.TimeoutExpired:
        return {'status': 'timeout', 'reason': f'command exceeded {timeout}s'}
    except Exception as ex:
        return {'status': 'error', 'reason': f'{type(ex).__name__}: {str(ex)[:160]}'}


def read_text(path, max_chars=1000):
    try:
        return Path(path).read_text(errors='replace').strip()[:max_chars]
    except OSError:
        return None


def meminfo():
    values = {}
    text = read_text('/proc/meminfo', 16000) or ''
    for key, value in re.findall(r'^(\w+):\s*(\d+)\s+kB', text, re.M):
        if key in {'MemTotal', 'MemAvailable', 'SwapTotal', 'SwapFree', 'MemFree'}:
            values[key + '_bytes'] = int(value) * 1024
    return values


def gpu_info_from_glx(out):
    text = out.get('stdout', '')
    values = {}
    for name, pattern in {
        'vendor': r'OpenGL vendor string:\s*(.+)',
        'renderer': r'OpenGL renderer string:\s*(.+)',
        'version': r'OpenGL (?:core profile )?version string:\s*(.+)',
    }.items():
        m = re.search(pattern, text)
        if m: values[name] = m.group(1).strip()
    renderer = values.get('renderer', '').lower()
    values['software_renderer_suspected'] = ('llvmpipe' in renderer or 'softpipe' in renderer)
    values['d3d12_renderer_reported'] = 'd3d12' in renderer
    return values


def get_windows_host():
    """CIM avoids serial numbers, username, device identifiers and addresses."""
    ps = shutil.which('powershell.exe')
    if not ps:
        return {'status': 'unavailable', 'reason': 'powershell.exe not available; Windows interop may be disabled'}
    script = r'''$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$cpu = @(Get-CimInstance -ClassName Win32_Processor | ForEach-Object {
    [pscustomobject]@{Name=$_.Name; Cores=$_.NumberOfCores;
      LogicalProcessors=$_.NumberOfLogicalProcessors; MaxClockMHz=$_.MaxClockSpeed}
})
$gpus = @(Get-CimInstance -ClassName Win32_VideoController | ForEach-Object {
    [pscustomobject]@{Name=$_.Name; DriverVersion=$_.DriverVersion;
      VideoProcessor=$_.VideoProcessor}
})
$cs = Get-CimInstance -ClassName Win32_ComputerSystem
$os = Get-CimInstance -ClassName Win32_OperatingSystem
$p = Join-Path $env:USERPROFILE '.wslconfig'
$settings = @{}
if(Test-Path -LiteralPath $p) {
  foreach($line in [System.IO.File]::ReadAllLines($p)) {
    if($line -match '^\s*(memory|swap|processors|guiApplications|gpuSupport)\s*=\s*([^#;]+)') {
      $settings[$matches[1]] = $matches[2].Trim()
    }
  }
}
$obj = [ordered]@{Status='ok'; CPU=$cpu; RAMBytes=[long]$cs.TotalPhysicalMemory;
  GPU=$gpus; WindowsVersion=$os.Version; WSLConfigPresent=[bool](Test-Path -LiteralPath $p);
  WSLConfig=$settings}
$obj | ConvertTo-Json -Compress -Depth 5
'''
    encoded = base64.b64encode(script.encode('utf-16le')).decode('ascii')
    result = run([ps, '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded], timeout=20, limit=16000)
    if result['status'] != 'ok':
        return {'status': result['status'], 'reason': result.get('stderr') or result.get('reason') or 'PowerShell error'}
    try:
        obj = json.loads(result['stdout'])
        # Force list shape even when CIM returns exactly one CPU/GPU.
        for key in ('CPU', 'GPU'):
            if isinstance(obj.get(key), dict): obj[key] = [obj[key]]
            elif obj.get(key) is None: obj[key] = []
        return obj
    except json.JSONDecodeError:
        return {'status': 'error', 'reason': 'PowerShell response not JSON; check Windows interop',
                'sample': result['stdout'][-240:]}


kernel = platform.release()
wsl = ('microsoft' in kernel.lower() or 'wsl' in kernel.lower())
cpudata = run(['lscpu'], timeout=4, limit=10000)
linux_cpu = {}
if cpudata['status'] == 'ok':
    for line in cpudata['stdout'].splitlines():
        if ':' not in line: continue
        k, v = (x.strip() for x in line.split(':', 1))
        if k in ('Model name', 'CPU(s)', 'Socket(s)', 'Core(s) per socket', 'Thread(s) per core', 'Architecture', 'Virtualization type'):
            linux_cpu[k] = v

osrelease = read_text('/etc/os-release', 5000) or ''
ubuntu_name = re.search(r'^PRETTY_NAME="?([^"\n]+)', osrelease, re.M)
linux = {
    'wsl_kernel_detected': wsl,
    'kernel_release': kernel,
    'distribution': ubuntu_name.group(1) if ubuntu_name else 'unknown',
    'cpu': {'logical_processors_affinity_available': len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else os.cpu_count(),
            'logical_processors_os': os.cpu_count(), 'lscpu': linux_cpu,
            'load_average_1m_5m_15m': list(os.getloadavg())},
    'memory': meminfo(),
    'cgroup': {f.split('/')[-1]: read_text(f) for f in (
        '/sys/fs/cgroup/memory.max', '/sys/fs/cgroup/memory.current',
        '/sys/fs/cgroup/cpu.max', '/sys/fs/cgroup/cpu.stat')},
    'gpu': {
        'dev_dxg_present': Path('/dev/dxg').exists(),
        'DISPLAY_set': bool(os.getenv('DISPLAY')),
        'WAYLAND_DISPLAY_set': bool(os.getenv('WAYLAND_DISPLAY')),
        'MESA_D3D12_DEFAULT_ADAPTER_NAME': os.getenv('MESA_D3D12_DEFAULT_ADAPTER_NAME', ''),
        'LIBGL_ALWAYS_SOFTWARE': os.getenv('LIBGL_ALWAYS_SOFTWARE', ''),
        'GALLIUM_DRIVER': os.getenv('GALLIUM_DRIVER', ''),
    }
}

if shutil.which('glxinfo'):
    glx = run(['glxinfo', '-B'], timeout=10)
    linux['gpu']['opengl_default_probe'] = {'status': glx['status'], **gpu_info_from_glx(glx),
                                             'diagnostic_error': glx.get('stderr', '')[:300] if glx['status'] != 'ok' else ''}
else:
    linux['gpu']['opengl_default_probe'] = {'status': 'unavailable', 'reason': 'Install mesa-utils to run glxinfo -B'}

if compare_gpu and shutil.which('glxinfo'):
    tests = {}
    for vendor in ('NVIDIA', 'Intel', 'AMD'):
        env = os.environ.copy()
        env['MESA_D3D12_DEFAULT_ADAPTER_NAME'] = vendor
        t = run(['glxinfo', '-B'], timeout=10, env=env)
        tests[vendor] = {'status': t['status'], **gpu_info_from_glx(t)}
    linux['gpu']['adapter_candidate_probes'] = tests

smi = shutil.which('nvidia-smi')
if not smi and Path('/usr/lib/wsl/lib/nvidia-smi').exists(): smi = '/usr/lib/wsl/lib/nvidia-smi'
if smi:
    nvidia = run([smi, '--query-gpu=name,memory.total,driver_version', '--format=csv,noheader'], timeout=8, limit=600)
    linux['gpu']['nvidia_query'] = {key: nvidia.get(key) for key in ('status', 'stdout', 'stderr')}
else:
    linux['gpu']['nvidia_query'] = {'status': 'unavailable', 'reason': 'No NVIDIA management utility; could be non-NVIDIA GPU'}

ps = run(['ps', '-eo', 'comm,%cpu,%mem,rss', '--sort=-%cpu'], timeout=5)
linux['processes_top_cpu'] = ps.get('stdout', '').splitlines()[:13]

reported_at = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
report = {'project': 'SAMSUNGAXI', 'report_schema': 1, 'captured_at_utc': reported_at,
          'scope': 'this Windows PC host + this WSL2 instance; do not apply to other projects or PCs',
          'windows_host': get_windows_host(), 'wsl2': linux,
          'gazebo': {'stats_requested': gazebo_stats, 'statistics': 'not_requested'},
          'notes': ['No system settings changed.',
                    'glxinfo renders in its own process: Gazebo renderer must also be checked in its logs.',
                    'nvidia-smi reports GPU visibility, not proof that Ogre2 uses the GPU.',
                    'Windows Win32_VideoController VRAM size is not used because it is often unreliable.']}
if gazebo_stats:
    gz = run(['gz', 'topic', '-e', '-t', '/world/restaurant/stats'], timeout=4, limit=7000)
    report['gazebo'] = {'stats_requested': True, 'statistics': gz['status'],
                        'first_sample': gz.get('stdout', '')[:3000] or gz.get('reason', '')}

notes = []
host = report['windows_host']
renderer = linux['gpu'].get('opengl_default_probe', {})
if renderer.get('software_renderer_suspected'):
    notes.append('WSLg OpenGL appears software-rendered (llvmpipe/softpipe); investigate drivers/WSLg GPU selection.')
elif renderer.get('d3d12_renderer_reported'):
    notes.append('WSLg OpenGL reports D3D12 renderer; check actual GPU name and Gazebo Ogre2 logs.')
else:
    notes.append('OpenGL renderer is unavailable or not D3D12; inspect renderer before tuning.')
if not linux['gpu']['dev_dxg_present']:
    notes.append('/dev/dxg is absent: verify WSL GPU virtualization and drivers.')
if host.get('Status') != 'ok' and host.get('status') != 'ok':
    notes.append('Windows host query unavailable; CPU/RAM/GPU host specs remain UNKNOWN.')
if linux['gpu']['LIBGL_ALWAYS_SOFTWARE'] in ('1', 'true'):
    notes.append('LIBGL_ALWAYS_SOFTWARE enabled: may force software rendering in WSL GUI.')
if linux['gpu']['GALLIUM_DRIVER'] in ('llvmpipe', 'softpipe'):
    notes.append('GALLIUM_DRIVER explicitly selects software rendering.')
report['interpretation_candidates'] = notes

outdir.mkdir(parents=True, exist_ok=True)
json_path = outdir / 'samsungaxi_hardware.json'
txt_path = outdir / 'samsungaxi_hardware.txt'
json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def gib(n):
    if n is None: return 'UNKNOWN'
    try: return f'{int(n)/1024**3:.2f} GiB'
    except (ValueError, TypeError): return str(n)

lines = [
    'SAMSUNGAXI_HARDWARE_PROFILE_READ_ONLY',
    f'CAPTURED_AT_UTC={reported_at}',
    f'WINDOWS_HOST_STATUS={host.get("Status", host.get("status", "unknown"))}',
    f'WINDOWS_CPU={"; ".join(str(c.get("Name", "unknown")) for c in host.get("CPU", [])) or "UNKNOWN"}',
    f'WINDOWS_CPU_LOGICAL={sum(int(c.get("LogicalProcessors") or 0) for c in host.get("CPU", [])) or "UNKNOWN"}',
    f'WINDOWS_RAM={gib(host.get("RAMBytes"))}',
    f'WINDOWS_GPU={"; ".join(str(g.get("Name", "unknown")) for g in host.get("GPU", [])) or "UNKNOWN"}',
    f'WSL_CPU_MODEL={linux_cpu.get("Model name", "UNKNOWN")}',
    f'WSL_CPU_LOGICAL_VISIBLE={linux["cpu"]["logical_processors_affinity_available"]}',
    f'WSL_MEM_TOTAL={gib(linux["memory"].get("MemTotal_bytes"))}',
    f'WSL_MEM_AVAILABLE={gib(linux["memory"].get("MemAvailable_bytes"))}',
    f'WSL_SWAP_TOTAL={gib(linux["memory"].get("SwapTotal_bytes"))}',
    f'WSL_DEV_DXG={linux["gpu"]["dev_dxg_present"]}',
    f'OPENGL_RENDERER={renderer.get("renderer", "UNKNOWN")}',
    f'NVIDIA_QUERY={linux["gpu"]["nvidia_query"].get("status", "UNKNOWN")}',
    f'WSL_CONFIG={json.dumps(host.get("WSLConfig", {}), ensure_ascii=False)}',
]
for i, note in enumerate(notes, 1): lines.append(f'CHECK_{i}={note}')
lines.extend(['SAMSUNGAXI_HARDWARE_DIAG_COMPLETE_NO_CHANGES',
              f'JSON_REPORT={json_path}', f'TEXT_REPORT={txt_path}'])
txt_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('\n'.join(lines))
PY