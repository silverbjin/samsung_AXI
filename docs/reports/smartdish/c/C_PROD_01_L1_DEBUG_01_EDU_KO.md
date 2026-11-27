# C-PROD-01 L1 debugging 01 — container Git safe.directory
- RED source 98e1ceaeab94b3f8928f0099954ab3f72572be7f, [run 45947063912](https://github.com/silverbjin/samsung_AXI/actions/runs/45947063912), job 140334078066.
- L0 8/8 PASS. L1 container initialization, checkout, apt success. First failure `fatal: detected dubious ownership in repository at '/__w/samsung_AXI/samsung_AXI'`, exit 128 at git rev-parse HEAD before ROS setup/build. L1 NOT_RUN, workflow FAIL.
- Cause: checkout sets safe.directory in temporary HOME; subsequent container shell has different Git config and root/runner workspace ownership. Not a model, DDS, or PyTorch problem.
- Minimal change: per-command `git -c safe.directory="$PWD" rev-parse HEAD`; no wildcard safe.directory, no permission changes or model changes. Next CI must pass source provenance before build.
- L0 artifact 15175365446 SHA256 ca81b9a78d2eb53121f6c9d63b4940dc92cab62e382c082ba62c464d8c8801ba.
- L1 failed artifact 15175635147 SHA256 a761763fbe14e73b37c1ab1f376f7034c097edd67069779c79b363833a33056d (empty source file, not success evidence).
