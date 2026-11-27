"""L0 only: verify service outcome classification, not actual shutdown."""
import sys
from pathlib import Path
from types import SimpleNamespace as NS
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from smartdish_a04_no_goal import manager_response
class Client:
    def __init__(self,response):self.response=response;self.calls=[]
    def service_is_ready(self):return True
    def call_async(self,request):
        self.calls.append(request)
        return NS(done=lambda:True,result=lambda:self.response)
def test_actual_response_shape_not_assumed():
    c=Client(NS(success=True,message="active"))
    p=NS(poll=lambda:None)
    r=manager_response(None,p,None,c,object(),1.)
    assert r["status"]=="RESPONSE" and r["success"] is True
    assert r["message"]=="active" and len(c.calls)==1
def test_negative_response_not_ack():
    c=Client(NS(success=False))
    r=manager_response(None,NS(poll=lambda:None),None,c,object(),1.)
    assert r["status"]=="RESPONSE" and r["success"] is False
