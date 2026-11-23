#!/usr/bin/env python3
"""S6 return-goal abort evidence classifier. Never retries or changes Nav2."""
import argparse,json
from pathlib import Path
from zipfile import ZipFile

def classify(evidence,summary):
    abort=evidence.get('nav2_goal_failure',{})
    if not abort:
        return {'first_failure':'NONE','scope':'NO_RECORDED_GOAL_ABORT'}
    server_ack='Timed out while waiting for action server to acknowledge goal request for follow_path' in summary
    fresh_scan=abort.get('scan_age_sec',999)<=.30
    fresh_odom=abort.get('odom_age_sec',999)<=.30
    return {
        'first_failure':'S6_RETURN_FOLLOW_PATH_ACK_TIMEOUT' if server_ack else 'S6_NAV2_ABORT_UNCLASSIFIED',
        'goal_label':abort.get('goal_label','UNKNOWN'),
        'action_status':abort.get('action_status'),
        'nav2_error_code':abort.get('nav2_error_code'),
        'nav2_error_msg':abort.get('nav2_error_msg'),
        'goal_error_m':abort.get('amcl_goal_error_m'),
        'distance_remaining_m':abort.get('last_feedback',{}).get('distance_remaining_m'),
        'sensor_fresh':fresh_scan and fresh_odom,
        'physical_odom_m':abort.get('physical_odom_max_displacement_m'),
        'nav2_return_succeeded':False,
        'root_cause':'NOT_CONFIRMED_FROM_BOUNDED_SUMMARY',
        'recommendation':'RETEST_EXACT_SAME_SHA_ONCE_BEFORE_CHANGING_NAV2'
    }
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--zip',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    with ZipFile(a.zip) as z:
        evidence=json.loads(z.read('generated/s6/real_vision_evidence.json'))
        summary=z.read('logs/ci-s3-summary.txt').decode('utf-8','replace')
    result=classify(evidence,summary)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(result['first_failure'])
if __name__=='__main__':main()
