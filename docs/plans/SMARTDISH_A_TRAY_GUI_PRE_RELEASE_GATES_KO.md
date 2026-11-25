# SmartDish A Tray GUI release preconditions (2026-11-24)

## Verified comparison

User WSL2 GUI batch at 6a4c2f2: ST-01 failed, ROS Image callback zero; original tar checksum verified. CI at same SHA passed headless 4 scenes but used Xvfb/llvmpipe. These are distinct render paths.

## Pre-release gates

- L0: Python/SDF/data and missing actual Image negative tests.
- L1: Jazzy ROS messages and bridge package.
- L2-H: real Gazebo headless, four separate physical dish scenes and PNG/pose evidence.
- L2-G/L2-COLD: GitHub Actions tray-l2-gui job runs real Gazebo server + GUI client via Xvfb, ST-01 real RGB/physical observation, on two separate cold-start runs with unique processes, partition, domain and seed. Requires actual post-GUI ROS image timestamps and full physical evidence. Does not repeat four scenes needlessly.
- L3: user's WSLg actual graphics environment and four scenes. CI GUI is not identical to WSLg; do not claim L3 PASS.

Do not use GZ topic advertisement or probe return code alone as proof of actual Image. Preserve source SHA, evidence original files and all failing logs. Do not modify S7, Nav2, Collision Monitor, A Navigation Adapter, B/C pipelines or existing AI OFF evidence. Hold Draft PR #45 unmerged.
