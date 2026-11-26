# A17 — GPU 유지 최소 환경 완화 후보 출고 (2026-11-26)

## 실제 Owner 증거와 원인 범위
A17 submitted TAR fb2952f63cf7b864ec3a7c5a54a47b9d98439c832b9ac9e0cb7f7821bfe2c671, sidecar and internal 26/26 verified. Native direct -11, software direct 0, both data PASS. GDB captured two SIGSEGV, first stack points to unmapped PC 0x7a99fba89b10 in __nptl_deallocate_tsd while SensorsPrivate::Stop joins thread; pre-shutdown map places PC in libd3d12core.so at file offset 0x2edb10, absent in fault-time map, si_code1/SEGV_MAPERR. Matches WSLg #1497 NVIDIA GLX reported offset and #1533 TSD mechanism. GDB inferior exit unknown after second stop; debugger rc0 not server PASS. All owned stopped. Actual registration/dlclose caller and vendor fix not proven. Strongly supported fault mechanism, not vendor-level resolution. See docs/reports/tasks/SMARTDISH_A17_OWNER_ROOT_AND_RETENTION_EDU_KO.md for detailed analysis and limits. No physical original published.

## Candidate exact execution pin
6eced423dbdab2aae9cf3e4a9f189349e46a469f
Server-only LD_PRELOAD of existing root-owned WSL libd3d12core.so (no hooks, no source binary modification, no global env). Existing native D3D12 NVIDIA RTX3060 profile required, same historical world, native pixel SHA 5a425c839947dc1bfb71e8b6c8d7636a4bf771b8cc9274c27067bb98fe490954, exact pin/clean/Jazzy/8.15.0/WSL preflight. Actual loaded D3D12 maps and same-environment GLX GPU corroboration, actual valid RGB, exit0 both server/bridge, SIGINT, all owned stopped. Records hashes of existing WSL core/d3d12 libraries; old binary hashes unavailable. Native hardware direct context proof not instrumented. If profile/driver or pixel output changed, HOLD, not silently approve. Prior baseline direct native/software and GDB not rerun; exactly one camera-only candidate. No production change or automatic adoption, no A15/A16 repeats. If fails submit diagnostic, no automatic repeat. A17 historical cleanup FAIL, production Contact HOLD, GT no approval.

## Actual CI and independent artifact audit
- #45758931528 SUCCESS: A17 8/8 tests, Platform 7/7, real exact Git pin and baseline. Actual Linux TSD analogue unretained -11 after DLCLOSE_RETURNED, retained 0 with TSD_DESTRUCTOR_RAN and JOINED. Artifact #15088348610 downloaded and rehashed ZIP 3796fc55069dc703cc593ba6d35b292963b17ae037b2dd3035957645ed3cf43f, CRC PASS, results JSON direct verified. This is an analogue, not WSL or Gazebo candidate success.
- #45758931409 SUCCESS: automatic A17 regression because shared diagnostic probe adds opt-in server env override. Actual GDB crash fixture and software direct/GDB Gazebo camera-only controls PASS. Both actual server/bridge0, no owned groups remain, 5 frames each identical prior Cloud pixel SHA e89a08017d7b374096394d0d232880d1b27d567ec12be384a478ed664562e24a. Artifact #15089375769 ZIP 54f96d4b66a7395c23a35e0471c1aa710a29b80466dfa3d4fdb885378d7ca7f7 downloaded/rehashed CRC PASS; TAR 262fa2cd8aa0e4389f8c7062995c988e4c61be094b6b2fe68621827189b7f41f, manifest18/18. No native D3D12 in Cloud.
- Common Platform push #45758931463 and PR #45758939444 SUCCESS. Automatically triggered full Restaurant MVP #45758939521 in progress at last check; not an A17 isolated candidate diagnostic release gate. No product/main merge.
- Native mitigation actual WSL2 NOT_RUN.

## Owner one-shot
Existing D3D12 environment unchanged. No new dependency installation. Uses a new home workspace and exact validated source. No GUI. The output filename remains a17_cleanup_evidence.tar.gz, report inside a17_retention_report.json distinguishes it from prior baseline.

```bash
(
set -Eeuo pipefail
PIN=6eced423dbdab2aae9cf3e4a9f189349e46a469f
curl -fsSLo "$HOME/a17_gpu_retention_bootstrap.sh" "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$PIN/scripts/a17_gpu_retention_bootstrap.sh"
SMARTDISH_A17_SOURCE_SHA="$PIN" bash "$HOME/a17_gpu_retention_bootstrap.sh"
)
```
Submit both a17_cleanup_evidence.tar.gz and .sha256 from generated_a17_retention; early bootstrap failure diagnostic pair if applicable. Expected A17_RETENTION_VERDICT=GPU_RETENTION_MINIMAL_MITIGATION_PASS or HOLD. If PASS, evidence only for camera-only mitigation with GPU profile retained. Product shutdown qualification with explicitly approved scoped profile is separate; no retroactive historical cleanup PASS or vendor fix. If HOLD, analyze first error, don't rerun baseline. A16/B-QA04/stable/E/main preserved. PR53 stays Draft.
