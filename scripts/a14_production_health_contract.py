"""R02 diagnostic-only contract. Empty ECM snapshots cannot prove freshness."""
from collections import defaultdict

ECM = 'GAZEBO_POSTUPDATE_ECM_SNAPSHOT'
ROS = 'ROS_CONTACT_HEADER_STAMP'


def pair_set(row):
    pairs = row.get('pairs', [])
    if not isinstance(pairs, list) or any(
        not isinstance(p, list) or len(p) != 2 or
        any(type(i) is not int or i <= 0 for i in p) or p[0] == p[1]
        for p in pairs
    ):
        raise ValueError('INVALID_COLLISION_PAIR')
    return {tuple(sorted(p)) for p in pairs}


def assess(expected, rows, ros, clocks, start, end, step, *, discovered, overflow=False):
    """Inputs are parsed raw observations; L0 callers use fixtures only.

    A diagnostic PASS means complete ECM snapshots plus >=1 exact positive ROS
    match, NOT freshness of empty components or full production health.
    """
    if not expected or step <= 0 or start <= 0 or end <= start or (end-start)%step:
        raise ValueError('INVALID_WINDOW')
    stamps = range(start, end+1, step)
    need = len(stamps)
    window = set(stamps)
    c = [t for t in clocks if type(t) is int and t > 0]
    clock_ok = (len(c) >= 2 and min(c) <= start and max(c) >= end and
                all(0 <= b-a <= 350_000_000 for a,b in zip(c,c[1:])) and
                c[-1] > c[0])
    ros_by = defaultdict(set)
    for row in ros:
        if row.get('topic') in expected and row.get('sim_ns') in window and row.get('source') == ROS:
            try: ros_by[row['topic'],row['sim_ns']].update(pair_set(row))
            except ValueError: pass
    sensors = {}
    for topic, identity in expected.items():
        seq = [r for r in rows if r.get('topic') == topic and r.get('sim_ns') in window]
        reasons = []
        if [r['sim_ns'] for r in seq] != list(stamps): reasons.append('MISSING_DUPLICATE_OR_REORDERED_STEP')
        identities = {(r.get('sensor_id'),r.get('collision_id')) for r in seq}
        if len(identities)!=1 or any(type(i) is not int or i<=0 for x in identities for i in x):
            reasons.append('SENSOR_OR_COLLISION_ID_INVALID')
        it = [r.get('iteration') for r in seq]
        if any(type(i) is not int or i<=0 for i in it) or any(b-a!=1 for a,b in zip(it,it[1:])):
            reasons.append('ITERATION_DISCONTINUITY')
        positive = matched = unmatched = 0
        empty = 0
        for r in seq:
            if any(r.get(k)!=v for k,v in identity.items()) or r.get('source')!=ECM or r.get('dt_ns')!=step or r.get('present') is not True:
                reasons.append('IDENTITY_SOURCE_OR_COMPONENT_INVALID'); continue
            try:
                pairs=pair_set(r)
                if r.get('count')!=len(r.get('pairs',[])) or any(r['collision_id'] not in p for p in pairs):
                    raise ValueError('INVALID_PAIR_COUNT_OR_OWNER')
            except ValueError:
                reasons.append('INVALID_PAIR_COUNT_OR_OWNER'); continue
            if pairs:
                positive+=1
                if pairs <= ros_by[topic,r['sim_ns']]: matched+=1
                else: unmatched+=1
            else: empty+=1
        complete=not reasons and len(seq)==need
        if not complete: status='ECM_COVERAGE_INCOMPLETE'
        elif positive==0: status='ECM_EMPTY_FRESHNESS_UNPROVEN'
        elif matched==0: status='ECM_POSITIVE_ROS_UNMATCHED'
        elif unmatched or empty: status='ECM_ROS_POSITIVE_PARTIAL_COVERAGE'
        else: status='ECM_ROS_POSITIVE_ALL_STEPS_MATCHED'
        sensors[topic]={'snapshot_coverage_pass':complete,'snapshot_steps':len(seq),
                        'expected_steps':need,'first_sim_ns':seq[0]['sim_ns'] if seq else None,
                        'last_sim_ns':seq[-1]['sim_ns'] if seq else None,
                        'sensor_collision_ids':[list(x) for x in sorted(identities,key=repr)],
                        'positive_steps':positive,'matched_positive_steps':matched,
                        'unmatched_positive_steps':unmatched,'empty_steps':empty,
                        'ros_publisher_discovered':discovered.get(topic,0)>0,
                        'status':status,'reasons':sorted(set(reasons)),
                        'empty_component_freshness_proven':False}
    diagnostic = (clock_ok and not overflow and all(s['snapshot_coverage_pass'] and s['ros_publisher_discovered'] for s in sensors.values()) and
                  any(s['matched_positive_steps']>0 for s in sensors.values()) and
                  all(s['positive_steps']==0 or s['matched_positive_steps']>0 for s in sensors.values()))
    return {'schema':1,'diagnostic_capture_pass':diagnostic,'start_ns':start,'end_ns':end,
            'step_ns':step,'clock_coverage_pass':clock_ok,'overflow':bool(overflow),'sensors':sensors,
            'production_contact_health':'HOLD','no_contact_inferred_from_silence':False,
            'rule_candidate':'UNKNOWN','human_approved':False,'label_status':'REVIEW_REQUIRED',
            'ground_truth':'NOT_OPERATOR_APPROVED'}
