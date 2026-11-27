// A04 actual per-physics-step witness. Read-only ECM, no component mutation.
#include <array>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <map>
#include <set>
#include <string>
#include <utility>
#include <gz/plugin/Register.hh>
#include <gz/sim/System.hh>
#include <gz/sim/Util.hh>
#include <gz/sim/EntityComponentManager.hh>
#include <gz/sim/components/Model.hh>
#include <gz/sim/components/Name.hh>
#include <gz/sim/components/Pose.hh>
#include <gz/sim/components/Collision.hh>
#include <gz/sim/components/ContactSensorData.hh>
#include <sdf/Element.hh>
namespace smartdish {
class A04Observer final : public gz::sim::System,
 public gz::sim::ISystemConfigure, public gz::sim::ISystemPostUpdate {
  using Entity=gz::sim::Entity;
  using ECM=gz::sim::EntityComponentManager;
  using Pair=std::pair<uint64_t,uint64_t>;
  using Names=std::pair<std::string,std::string>;
  std::ofstream ticks, identities;
  std::map<Pair,Names> known;
  std::array<std::string,4> models{{"waffle_pi","smartdish_product_dish_00","smartdish_product_dish_01","smartdish_product_dish_02"}};
  uint64_t rows=0;
  bool invalid=false;
 public:
  void Configure(const Entity &,const std::shared_ptr<const sdf::Element>&s,ECM &,gz::sim::EventManager &)override {
    if(!s||!s->HasElement("output"))return;
    auto prefix=s->Get<std::string>("output");
    ticks.open(prefix+"_ticks.tsv",std::ios::out|std::ios::trunc);
    identities.open(prefix+"_pairs.tsv",std::ios::out|std::ios::trunc);
    ticks<<"sim_ns\titeration\tdt_ns\tcontact_components\tpair_count\tpairs";
    for(const auto &n:models)for(const auto *k:{"id","x","y","z","qx","qy","qz","qw"})ticks<<'\t'<<n<<'_'<<k;
    ticks<<'\n'<<std::setprecision(17);
    identities<<"id1\tid2\tname1\tname2\n";
  }
  void PostUpdate(const gz::sim::UpdateInfo &info,const ECM &ecm)override {
    if(info.paused||!ticks||!identities||invalid)return;
    auto ns=std::chrono::duration_cast<std::chrono::nanoseconds>(info.simTime).count();
    auto dt=std::chrono::duration_cast<std::chrono::nanoseconds>(info.dt).count();
    if(dt<=0)return;
    if(++rows>2000000){ticks<<"OVERFLOW\n";ticks.flush();invalid=true;return;}
    using namespace gz::sim::components;
    std::array<Entity,4> ids{};
    std::array<gz::math::Pose3d,4> poses{};
    ecm.Each<Model,Name,Pose>([&](const Entity &id,const Model*,const Name *n,const Pose*){
      for(size_t i=0;i<models.size();++i)if(n->Data()==models[i]){
        if(ids[i]!=0){invalid=true;return false;}
        ids[i]=id;poses[i]=gz::sim::worldPose(id,ecm);
      }
      return true;
    });
    uint64_t components=0;std::set<Pair> observed;
    ecm.Each<Collision,ContactSensorData>([&](const Entity &,const Collision*,const ContactSensorData *d){
      ++components;
      for(const auto &c:d->Data().contact()){
        auto a=c.collision1().id(),b=c.collision2().id();
        std::string na=c.collision1().name(),nb=c.collision2().name();
        if(a>b){std::swap(a,b);std::swap(na,nb);}
        Pair key{a,b};Names names{na,nb};
        if(!a||!b||na.empty()||nb.empty()||na.find_first_of("\t\r\n")!=std::string::npos||nb.find_first_of("\t\r\n")!=std::string::npos){invalid=true;return false;}
        auto [it,fresh]=known.emplace(key,names);
        if(fresh){identities<<a<<'\t'<<b<<'\t'<<na<<'\t'<<nb<<'\n';identities.flush();}
        else if(it->second!=names){invalid=true;return false;}
        observed.insert(key);
      }
      return true;
    });
    if(invalid){ticks<<"INVALID_IDENTITY\n";ticks.flush();return;}
    ticks<<ns<<'\t'<<info.iterations<<'\t'<<dt<<'\t'<<components<<'\t'<<observed.size()<<'\t';
    bool first=true;for(auto [a,b]:observed){if(!first)ticks<<';';first=false;ticks<<a<<':'<<b;}
    if(first)ticks<<'-';
    for(size_t i=0;i<models.size();++i){auto p=poses[i].Pos();auto q=poses[i].Rot();ticks<<'\t'<<ids[i]<<'\t'<<p.X()<<'\t'<<p.Y()<<'\t'<<p.Z()<<'\t'<<q.X()<<'\t'<<q.Y()<<'\t'<<q.Z()<<'\t'<<q.W();}
    ticks<<'\n';if(rows%100==0)ticks.flush();
  }
};}
GZ_ADD_PLUGIN(smartdish::A04Observer,gz::sim::System,gz::sim::ISystemConfigure,gz::sim::ISystemPostUpdate)
GZ_ADD_PLUGIN_ALIAS(smartdish::A04Observer,"smartdish::A04Observer")
