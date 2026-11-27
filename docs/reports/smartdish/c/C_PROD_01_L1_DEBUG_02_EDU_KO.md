# C-PROD-01 L1 debugging 02 — rclpy Node 속성 충돌
- source 16d7596e99270d584beb0cf6f2b01c0b6a0eb0d0, PR [run 45947183289](https://github.com/silverbjin/samsung_AXI/actions/runs/45947183289), job 140334461052. Branch push run 45947179939 also triggered. L0 success, L1 failure.
- safe.directory fix verified: exact checkout, colcon build finished, installed-origin check and entrypoint listing passed.
- First actual ROS failure: installed product_stability_inference_node.py line 49 calls add_on_set_parameters_callback(self._parameters); rclpy/node.py raises TypeError: Callback must be callable, got dict.
- Cause: rclpy Node owns instance attribute _parameters (dict), shadowing subclass method with same name. Not torch nor missing model.
- Minimal change: rename method to _on_threshold_parameters and update registration; no model/runtime/threshold policy change.
- Failed L1 artifact 15175325740 SHA256 fcc68b5fa6d46ce3f394274bc302b149f8e55a0004cef12ff8734a7590a315ba; L0 artifact 15175610502 SHA256 c4150de41d03964ad1949291adc0594bdd86a54d37dd57a536e2703726917f27.
- Next CI must prove real parameter service and DDS, not just build.
