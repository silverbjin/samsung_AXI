"""S5 L0 regression: operator delay must not stop ROS callbacks or bypass safety."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SMOKE=ROOT/'scripts/ci_s3_amcl_smoke.py'

def test_s5_owner_no_blocking_input_while_ros_executor_waits():
    src=SMOKE.read_text()
    assert 'answer=input(' not in src, "RED: synchronous input() starves ROS callbacks"
    assert 'wait_for_owner_approval(' in src
    assert 'S5_OWNER_FRESH_SCAN_ODOM_AFTER_APPROVAL' in src

def test_s5_pre_goal_stale_gate_is_not_weakened():
    src=SMOKE.read_text()
    assert "time.monotonic()-state['scan_t']>8 or time.monotonic()-state['odom_t']>8" in src
    assert "NAV_PREGOAL_SENSOR_STALE_" in src
    assert "S5_OWNER_GOAL_CONFIRMATION_MISSING" in src


def test_delayed_tty_confirmation_keeps_spin_callbacks_active():
    import os,threading,time,sys
    sys.path.insert(0,str(ROOT/'scripts'))
    from s5_owner_approval import wait_for_owner_approval
    master,slave=os.openpty()
    calls=[0]
    try:
        def sender():
            time.sleep(1.0)
            os.write(master,b'YES-S5-LIVE-GOALS\n')
        t=threading.Thread(target=sender,daemon=True)
        t.start()
        def spin(interval):
            calls[0]+=1
            time.sleep(min(interval,.015))
        with os.fdopen(slave,'r') as stream:
            waited=wait_for_owner_approval(spin,stream=stream,timeout_sec=5)
        t.join(timeout=2)
        assert waited>=.8
        assert calls[0]>=30,"ROS subscriptions must keep spinning through human delay"
    finally:
        os.close(master)

def test_wrong_or_eof_confirmation_fails_closed():
    import os,sys,pytest
    sys.path.insert(0,str(ROOT/'scripts'))
    from s5_owner_approval import wait_for_owner_approval
    for text in (b'NO\n',b''):
        reader,writer=os.pipe()
        try:
            if text:os.write(writer,text)
            os.close(writer)
            with os.fdopen(reader,'r') as stream:
                with pytest.raises(RuntimeError,match='S5_OWNER_GOAL_CONFIRMATION_MISSING'):
                    wait_for_owner_approval(lambda _:None,stream=stream,timeout_sec=.3)
        finally:
            pass

def test_fresh_after_approval_must_observe_both_real_callback_counts():
    import sys
    sys.path.insert(0,str(ROOT/'scripts'))
    from s5_owner_approval import wait_for_fresh_sensors
    monotonic=[100.0]
    sensor={'scan':4,'odom':5,'scan_t':99.0,'odom_t':99.0}
    def tick():
        return monotonic[0]
    def spin(delta):
        monotonic[0]+=.2
        # New scan and odom AFTER approval, not pre-existing readings.
        if monotonic[0]>=100.4:
            sensor['scan']+=1
            sensor['scan_t']=monotonic[0]
        if monotonic[0]>=100.8:
            sensor['odom']+=1
            sensor['odom_t']=monotonic[0]
    snapshot=lambda:(sensor['scan'],sensor['odom'],sensor['scan_t'],sensor['odom_t'])
    actual=wait_for_fresh_sensors(spin,snapshot,timeout_sec=1.5,clock=tick)
    assert actual['scan_count_after_approval']>0
    assert actual['odom_count_after_approval']>0
    assert actual['scan_age_sec']>=0 and actual['odom_age_sec']>=0

def test_stopped_scan_or_odom_still_blocks_goals():
    import sys,pytest
    sys.path.insert(0,str(ROOT/'scripts'))
    from s5_owner_approval import wait_for_fresh_sensors
    for freeze in ('scan','odom'):
        now=[50.0]
        samples={'scan':3,'odom':7,'scan_t':49.9,'odom_t':49.9}
        def spin(delta):
            now[0]+=.2
            if freeze!='scan':
                samples['scan']+=1;samples['scan_t']=now[0]
            if freeze!='odom':
                samples['odom']+=1;samples['odom_t']=now[0]
        snapshot=lambda:(samples['scan'],samples['odom'],samples['scan_t'],samples['odom_t'])
        with pytest.raises(RuntimeError,match='TIMEOUT_S5_OWNER_FRESH_SCAN_ODOM_AFTER_APPROVAL'):
            wait_for_fresh_sensors(spin,snapshot,timeout_sec=1.0,clock=lambda:now[0])
