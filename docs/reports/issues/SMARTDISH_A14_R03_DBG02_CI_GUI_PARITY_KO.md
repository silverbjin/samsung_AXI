# R03 DBG02 — 실제 생산 GUI 경로와 환경 격리

Cloud #45728116649 headless production used Xvfb + llvmpipe; Owner D3D12 + XWayland failed Context creation. New R03-only wrapper defaults to GUI software client (XCB, llvmpipe, LIBGL_ALWAYS_SOFTWARE=1), removes NVIDIA adapter only from GUI child env. Server and ROS retain original env. No .bashrc/system changes. Native GUI opt-in; no automatic rerun/fallback. Qt/GLX error root proven, D3D12 device removal cause not proven. Cloud software success is not WSLg GPU success.

CI normal actual production GUI and deliberate SIGABRT of owned real GUI process group after observation unpause (CI-only flag) are distinct experiments; no synthetic RGB/physics. Driver captures legacy rc, rechecks actual archive before accepting exact late GUI error. Startup failure or missing archive remains HOLD; no blanket nonzero acceptance. Original A13 code unchanged. CI pending at code commit.
