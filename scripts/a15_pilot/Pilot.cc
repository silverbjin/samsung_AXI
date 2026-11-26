// A15: same declared torque intervention for every loaded scene.
// Physics poses are actual ECM world poses. No pose or contact payload is written.
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <memory>
#include <string>
#include <gz/plugin/Register.hh>
#include <gz/sim/System.hh>
#include <gz/sim/EntityComponentManager.hh>
#include <gz/sim/Link.hh>
#include <gz/sim/Util.hh>
#include <gz/sim/components/Model.hh>
#include <gz/sim/components/Link.hh>
#include <gz/sim/components/Sensor.hh>
#include <gz/sim/components/Name.hh>
#include <gz/sim/components/ParentEntity.hh>
#include <sdf/Element.hh>
namespace smartdish {
class A15Pilot final : public gz::sim::System, public gz::sim::ISystemConfigure,
 public gz::sim::ISystemPreUpdate, public gz::sim::ISystemPostUpdate {
 using Entity=gz::sim::Entity; using ECM=gz::sim::EntityComponentManager;
 std::ofstream out,trigger;
 std::int64_t start=0,duration=0; double torque=0;
 Entity target=gz::sim::kNullEntity; std::uint64_t rows=0;
 static std::int64_t ns(const gz::sim::UpdateInfo &i) {
  return std::chrono::duration_cast<std::chrono::nanoseconds>(i.simTime).count();
 }
 void pose(const gz::sim::UpdateInfo &i,const ECM &ecm,Entity id,const std::string &name) {
  if (++rows>80000) { if(rows==80001) out<<"OVERFLOW\n"; return; }
  const auto p=gz::sim::worldPose(id,ecm);
  out<<ns(i)<<'\t'<<i.iterations<<'\t'<<name<<'\t'<<id<<'\t'
     <<p.Pos().X()<<'\t'<<p.Pos().Y()<<'\t'<<p.Pos().Z()<<'\t'
     <<p.Rot().X()<<'\t'<<p.Rot().Y()<<'\t'<<p.Rot().Z()<<'\t'<<p.Rot().W()<<'\n';
 }
public:
 void Configure(const Entity &,const std::shared_ptr<const sdf::Element> &s,ECM &,gz::sim::EventManager &) override {
  out.open(s->Get<std::string>("output"));trigger.open(s->Get<std::string>("trigger_output"));
  start=s->Get<std::uint64_t>("trigger_ns");duration=s->Get<std::uint64_t>("duration_ns");torque=s->Get<double>("torque_nm");
  out<<std::setprecision(17)<<"sim_ns\titeration\tentity\tentity_id\tx\ty\tz\tqx\tqy\tqz\tqw\n";
  trigger<<std::setprecision(17)<<"sim_ns\titeration\tlink_id\ttorque_y_nm\n";
  out.flush();trigger.flush();
 }
 void PreUpdate(const gz::sim::UpdateInfo &i,ECM &ecm) override {
  if(i.paused || ns(i)<start || ns(i)>=start+duration || !trigger) return;
  using namespace gz::sim::components;
  if(target==gz::sim::kNullEntity) {
   const auto model=ecm.EntityByComponents(Model(),Name("dish_02"));
   if(model!=gz::sim::kNullEntity) target=ecm.EntityByComponents(Link(),ParentEntity(model),Name("body"));
  }
  if(target==gz::sim::kNullEntity) return;
  gz::sim::Link(target).AddWorldWrench(ecm,gz::math::Vector3d(0,0,0),gz::math::Vector3d(0,torque,0));
  trigger<<ns(i)<<'\t'<<i.iterations<<'\t'<<target<<'\t'<<torque<<'\n';trigger.flush();
 }
 void PostUpdate(const gz::sim::UpdateInfo &i,const ECM &ecm) override {
  if(i.paused || !out) return;
  using namespace gz::sim::components;
  ecm.Each<Model,Name>([&](const Entity &id,const Model *,const Name *n){
   const auto &name=n->Data();
   if(name=="dish_01"||name=="dish_02"||name=="tray_platform") pose(i,ecm,id,name);
   return true;
  });
  ecm.Each<Sensor,Name>([&](const Entity &id,const Sensor *,const Name *n){
   if(n->Data()=="smartdish_tray_rgb") pose(i,ecm,id,"camera");
   return true;
  });
  out.flush();
 }
};
}
GZ_ADD_PLUGIN(smartdish::A15Pilot,gz::sim::System,gz::sim::ISystemConfigure,gz::sim::ISystemPreUpdate,gz::sim::ISystemPostUpdate)
GZ_ADD_PLUGIN_ALIAS(smartdish::A15Pilot,"smartdish::A15Pilot")
