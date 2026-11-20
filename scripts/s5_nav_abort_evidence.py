"""Fail-closed, ROS-free evidence formatter for a real Nav2 Action abort.

Never changes goal logic, time limits, controller or safety thresholds.
Existing successful S5 Nav2 L3 may not be rewritten or cleared.
"""
import math


def nav_abort_snapshot(*,label,status,action_result,state,start_odom,
                       before_track,goal_target,now,goal_elapsed,last_feedback):
    track=state.get('odom_track',[])[before_track:]
    displacement=None
    if start_odom is not None:
        displacement=max((math.dist(start_odom,xy) for xy in track),default=0.)
    amcl=state.get('amcl_pose')
    error=None if amcl is None else math.dist(amcl,goal_target)
    code=getattr(action_result,'error_code',None)
    message=getattr(action_result,'error_msg',None)
    return {
        'goal_label':str(label),
        'goal_sent':True,
        'action_status':int(status),
        'nav2_error_code':int(code) if code is not None else None,
        'nav2_error_msg':str(message) if message else None,
        'goal_map_xy':list(goal_target),
        'amcl_pose_xy':list(amcl) if amcl is not None else None,
        'amcl_goal_error_m':round(error,4) if error is not None else None,
        'physical_odom_max_displacement_m':round(displacement,4) if displacement is not None else None,
        'scan_count':int(state.get('scan',0)),
        'scan_age_sec':round(max(0.,now-state['scan_t']),3) if state.get('scan_t') else None,
        'odom_age_sec':round(max(0.,now-state['odom_t']),3) if state.get('odom_t') else None,
        'elapsed_wall_sec':round(goal_elapsed,3),
        'last_feedback':dict(last_feedback),
        'diagnostic_limit':'NAV2_CAUSE_UNCONFIRMED_UNTIL_ERROR_AND_SERVER_LOG_REVIEW',
    }
