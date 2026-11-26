# Executed inside GDB, never imported by normal Python.
# No core dump, no root, no attach to an unrelated process.
import gdb,os,json,signal
from pathlib import Path
out=Path(os.environ["A17_GDB_OUT"])
status={"inferior_pid":None,"inferior_exit_code":None,"inferior_exit_signal":None,"stops":[],"stack_captured":False,"debugger_error":None}
def write():
    tmp=out/"gdb_status.tmp"
    tmp.write_text(json.dumps(status,indent=2)+"\n")
    tmp.replace(out/"gdb_status.json")
def on_stop(event):
    if isinstance(event,gdb.SignalEvent):status["stops"].append(event.stop_signal)
def on_exit(event):
    status["inferior_exit_code"]=getattr(event,"exit_code",None)
    try:
        s=gdb.parse_and_eval("$_exitsignal")
        if s.type.code!=gdb.TYPE_CODE_VOID:status["inferior_exit_signal"]=int(s)
    except (gdb.error,ValueError):pass
    write()
try:
    for cmd in ("set confirm off","set pagination off","set debuginfod enabled off","set disable-randomization off","set startup-with-shell off","handle SIGINT nostop noprint pass","handle SIGTERM nostop noprint pass","handle SIGSEGV stop print pass","handle SIGABRT stop print pass"):
        gdb.execute(cmd)
    gdb.execute("starti")
    pid=gdb.selected_inferior().pid
    status["inferior_pid"]=pid
    status["start_ticks"]=Path("/proc",str(pid),"stat").read_text().rsplit(")",1)[1].split()[19]
    write()
    gdb.events.stop.connect(on_stop);gdb.events.exited.connect(on_exit)
    gdb.execute("continue")
    if gdb.selected_inferior().pid and status["stops"] and status["stops"][-1] in ("SIGSEGV","SIGABRT"):
        with (out/"crash_stack.txt").open("x") as f:
            for cmd in ("thread apply all bt 24","info sharedlibrary","info proc mappings","p $_siginfo"):
                f.write("\n=== "+cmd+" ===\n")
                try:f.write(gdb.execute(cmd,to_string=True))
                except gdb.error as exc:f.write("GDB_COMMAND_ERROR: "+str(exc)+"\n")
        status["stack_captured"]=True
        write()
        gdb.execute("continue")  # deliver original signal, never suppress it
    if gdb.selected_inferior().pid:status["debugger_error"]="INFERIOR_STILL_STOPPED"
except Exception as exc:status["debugger_error"]=type(exc).__name__+": "+str(exc)
finally:write()
