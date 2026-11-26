// Independent read-only native Gazebo subscriber. This is not a publisher tap.
#include <atomic>
#include <chrono>
#include <csignal>
#include <fstream>
#include <functional>
#include <iostream>
#include <mutex>
#include <string>
#include <thread>
#include <gz/transport/Node.hh>
#include <gz/msgs/contacts.pb.h>
namespace { volatile std::sig_atomic_t done=0; void stop(int){done=1;} }
int main(int argc,char **argv){
 if(argc<3)return 2;
 std::signal(SIGINT,stop);std::signal(SIGTERM,stop);
 std::ofstream out(argv[1]);if(!out)return 2;
 out<<"topic\tsim_ns\treceive_monotonic_ns\tpairs\n";out.flush();
 std::mutex mu;std::size_t count=0;bool overflow=false;
 {
  gz::transport::Node node;
  for(int i=2;i<argc;++i){
   const std::string topic=argv[i];
   std::function<void(const gz::msgs::Contacts&)> cb=[&,topic](const gz::msgs::Contacts &msg){
    std::lock_guard<std::mutex> lock(mu);
    if(count++>=150000){if(!overflow){out<<"OVERFLOW\n";out.flush();overflow=true;}return;}
    const auto &stamp=msg.header().stamp();
    const auto t=static_cast<std::int64_t>(stamp.sec())*1000000000LL+stamp.nsec();
    const auto wall=std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();
    out<<topic<<'\t'<<t<<'\t'<<wall<<'\t';
    bool first=true;for(const auto &x:msg.contact()){if(!first)out<<';';first=false;out<<x.collision1().id()<<':'<<x.collision2().id();}
    out<<'\n';out.flush();
   };
   if(!node.Subscribe<gz::msgs::Contacts>(topic,cb))return 2;
  }
  std::cout<<"A16_NATIVE_SUBSCRIBED"<<std::endl;
  while(!done)std::this_thread::sleep_for(std::chrono::milliseconds(30));
 }
 return overflow?2:0;
}
