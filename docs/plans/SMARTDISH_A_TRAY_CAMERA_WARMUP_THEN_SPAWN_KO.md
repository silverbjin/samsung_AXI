# A-13 camera pre-warm before dynamic dish spawn (MVP design)

## Actual failure boundary

On [L2-G #45335616574](https://github.com/silverbjin/samsung_AXI/actions/runs/45335616574), an actual GZ Image protobuf echo was saved (3,664,716 bytes, SHA 74b56105...), but ROS Image callback was 0 at sim 0.315s. This proves the Gazebo camera publishes; first-frame GZ->ROS bridge/discovery or delivery latency occurs before sufficient sensor frames have been delivered. A single Gazebo 5Hz frame at sim 0.2s can be lost while the bridge and transport are getting ready.

## Minimal physical-data-safe mitigation

Do not simply advance the physics until a later image: unstable dishes can fall and leak the outcome into the training input. Instead retain the complete original scenario.sdf and original seed, initial pose, mass, friction, collision and inertia. Generate sensor_preflight.sdf by omitting only dynamic dish models and save identical unmodified per-dish SDFs. Run the real GZ RGB sensor and ROS bridge with an empty tray long enough to receive *multiple* actual ROS Image frames. Then create the original dynamic dish models using official Gazebo UserCommands /world/smartdish_tray/create and gz.msgs.EntityFactory. Reject if actual entity poses or a new post-spawn RGB Image are missing. Begin the 10s physics observation only after validating the capture-time poses and a newly received image.

This design preserves the pre-outcome training image protocol, does not freeze dishes, and keeps full scenario SDF as physical intent evidence. Record the sensor world and dynamic spawn manifest hashes separately. Same execution mode for CI headless and CI GUI; prior AI OFF untouched. Do not claim resolved until same SHA actual L2-H 4/4 and GUI 2/2 PASS.
