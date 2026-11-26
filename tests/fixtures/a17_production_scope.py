"""Actual Linux process scope fixture only. Not WSL, Gazebo, or hardware proof."""
import hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/"scripts"));sys.path.insert(0,str(ROOT/"tests"))
import a17_production_profile as p
from test_a17_production_profile import fake_run,ENV
from smartdish_platform.lifecycle import stop_owned

def run(out):
    out=Path(out).resolve();out.mkdir(exist_ok=False,parents=True)
    c=out/"fixture.c";c.write_text("int a17_fixture(void){return 1;}\n")
    core=str(out/"fixture_core.so");driver=str(out/"fixture_driver.so")
    for name in (core,driver):subprocess.run(["gcc","-shared","-fPIC",str(c),"-o",name],check=True,timeout=15)
    hashes={x:hashlib.sha256(Path(x).read_bytes()).hexdigest() for x in (core,driver)}
    def inventory(name,h):return {"path":name,"realpath":name,"sha256":h,"size_bytes":Path(name).stat().st_size}
    env=dict(os.environ);env.pop("LD_PRELOAD",None);env.pop("LD_AUDIT",None);env.pop("MESA_LOADER_DRIVER_OVERRIDE",None);env.pop("LIBGL_ALWAYS_SOFTWARE",None);env.update(ENV)
    # Only the test patches hardware/trust inputs. Production accepts no fixture switch.
    processes=[];report={"scope":"LINUX_PROCESS_SCOPE_FIXTURE_NOT_WSL_NOT_GAZEBO","hardware_checks_mocked":True,"actual_procfs_and_exit_codes":True,"roles":{}}
    code="import ctypes,os,signal,sys,time; ctypes.CDLL(sys.argv[1]) if sys.argv[1] else None; signal.signal(signal.SIGINT,lambda *x:sys.exit(0)); print('READY',flush=True); time.sleep(45)"
    try:
        with patch.object(p,"CORE",core),patch.object(p,"LIBRARIES",hashes),patch.object(p,"_run",side_effect=fake_run),patch.object(p,"_trusted_library",side_effect=inventory):
            server_env,record=p.prepare(env,p.RETAIN,"OWNER_WSL2")
            for role in ("server","native_contact","rgb_bridge","contact_bridge","gui"):
                child=subprocess.Popen([sys.executable,"-c",code,driver if role=="server" else ""],env=server_env if role=="server" else env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
                processes.append((role,child))
                # bounded readiness using select on pipe, no unbounded readline
                import select
                if not select.select([child.stdout],[],[],5)[0] or child.stdout.readline().strip()!="READY":raise RuntimeError("FIXTURE_READY")
                raw=Path("/proc",str(child.pid),"environ").read_bytes()
                preload=[x.decode() for x in raw.split(b"\0") if x.startswith(b"LD_PRELOAD=")]
                maps=Path("/proc",str(child.pid),"maps").read_text()
                report["roles"][role]={"preload":preload,"fixture_core_mapped":core in maps,"fixture_driver_mapped":driver in maps}
                assert preload==(["LD_PRELOAD="+core] if role=="server" else [])
                assert (core in maps)==(role=="server") and (driver in maps)==(role=="server")
            server=processes[0][1]
            p.observe(server,record)
            p.observe(server,record,"runtime_observation_pre_shutdown")
            report["runtime_observation"]=record["runtime_observation"]
            report["runtime_observation_pre_shutdown"]=record["runtime_observation_pre_shutdown"]
            rows=[]
            for role,child in reversed(processes):
                row=stop_owned(child,int_timeout=3,term_timeout=2,kill_timeout=2);row["role"]=role
                try:os.killpg(child.pid,0);row["process_group_remaining"]=True
                except ProcessLookupError:row["process_group_remaining"]=False
                rows.append(row)
            report["processes"]=rows
            assert p.cleanup_result(record,rows,"PASS",all(x["stopped"] and not x["process_group_remaining"] for x in rows))=="PASS"
            report["verdict"]="PASS_FIXTURE_ONLY"
            assert "LD_PRELOAD" not in env
    finally:
        for _,child in processes:
            if child.poll() is None:stop_owned(child,int_timeout=2,term_timeout=2,kill_timeout=2)
            child.stdout.close();child.stderr.close()
        (out/"results.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("A17_08_ACTUAL_PROCESS_SCOPE_FIXTURE_PASS_NOT_WSL")
if __name__=="__main__":run(sys.argv[1])
