// R02-2: metadata challenge; never write Contact payload or publish messages.
#include <chrono>
#include <cstdint>
#include <fstream>
#include <memory>
#include <string>
#include <unordered_set>
#include <gz/plugin/Register.hh>
#include <gz/sim/System.hh>
#include <gz/sim/EntityComponentManager.hh>
#include <gz/sim/components/Collision.hh>
#include <gz/sim/components/ContactSensor.hh>
#include <gz/sim/components/ContactSensorData.hh>
#include <gz/sim/components/Name.hh>
#include <gz/sim/components/ParentEntity.hh>
#include <sdf/Element.hh>

namespace smartdish {
class A14ProductionHealth final : public gz::sim::System,
    public gz::sim::ISystemConfigure, public gz::sim::ISystemPreUpdate,
    public gz::sim::ISystemUpdate, public gz::sim::ISystemPostUpdate {
  using ECM = gz::sim::EntityComponentManager;
  using Entity = gz::sim::Entity;
  std::ofstream out;
  std::uint64_t rows = 0;
  bool overflow = false;
  bool control = false;
  std::unordered_set<Entity> armed, late;
  std::uint64_t armIteration = 0;
  static constexpr std::uint64_t limit = 100000;
  static std::string name(Entity e, const ECM &ecm) {
    const auto *c = ecm.Component<gz::sim::components::Name>(e);
    return c ? c->Data() : "";
  }
public:
  void Configure(const Entity &, const std::shared_ptr<const sdf::Element> &sdf,
      ECM &, gz::sim::EventManager &) override {
    if (sdf && sdf->HasElement("output"))
      out.open(sdf->Get<std::string>("output"), std::ios::out | std::ios::trunc);
    if (sdf && sdf->HasElement("late_control")) control = sdf->Get<bool>("late_control");
    if (out) {
      out << "sim_ns\titeration\tdt_ns\ttopic\tmodel\tsensor\tcollision"
             "\tsensor_id\tcollision_id\tpresent\tcount\tpairs\tarmed\tpost_state\tlate_control\n";
      out.flush();
    }
  }

  // Mark only change bookkeeping, never protobuf contents. Physics Update
  // calls SetChanged(NoChange/PeriodicChange) for every visited collision.
  void PreUpdate(const gz::sim::UpdateInfo &info, ECM &ecm) override {
    armed.clear(); late.clear();
    armIteration = info.iterations;
    if (info.paused || !out || overflow) return;
    using namespace gz::sim::components;
    ecm.Each<Collision, ContactSensorData>(
        [&](const Entity &id, const Collision *, const ContactSensorData *) {
          ecm.SetChanged(id, ContactSensorData::typeId, gz::sim::ComponentState::OneTimeChange);
          if (ecm.ComponentState(id, ContactSensorData::typeId) ==
              gz::sim::ComponentState::OneTimeChange) armed.insert(id);
          return true;
        });
  }

  // Deliberately re-arm after Physics on a few known control steps. If a
  // generic reset between Update and PostUpdate masked this, the test fails.
  // This is used ONLY for the independent diagnostic, never production trials.
  void Update(const gz::sim::UpdateInfo &info, ECM &ecm) override {
    if (!control || info.paused || info.iterations % 100 != 0) return;
    for (const Entity id : armed) {
      ecm.SetChanged(id, gz::sim::components::ContactSensorData::typeId,
                     gz::sim::ComponentState::OneTimeChange);
      if (ecm.ComponentState(id, gz::sim::components::ContactSensorData::typeId) ==
          gz::sim::ComponentState::OneTimeChange) late.insert(id);
    }
  }

  void PostUpdate(const gz::sim::UpdateInfo &info, const ECM &ecm) override {
    if (info.paused || !out || overflow) return;
    using namespace gz::sim::components;
    const auto stamp = std::chrono::duration_cast<std::chrono::nanoseconds>(
        info.simTime).count();
    const auto dt = std::chrono::duration_cast<std::chrono::nanoseconds>(
        info.dt).count();
    ecm.Each<ContactSensor, ParentEntity>(
        [&](const Entity &sensor, const ContactSensor *contact,
            const ParentEntity *parent) {
          if (!contact->Data() || !contact->Data()->HasElement("contact")) return true;
          auto spec = contact->Data()->GetElement("contact");
          if (!spec || !spec->HasElement("topic") || !spec->HasElement("collision"))
            return true;
          const auto topic = spec->Get<std::string>("topic");
          if (topic.rfind("/smartdish/tray/contact/", 0) != 0) return true;
          const auto collision = spec->Get<std::string>("collision");
          const auto link = parent->Data();
          const auto *modelParent = ecm.Component<ParentEntity>(link);
          const auto model = modelParent ? name(modelParent->Data(), ecm) : "";
          const auto children = ecm.ChildrenByComponents(link, Collision(), Name(collision));
          const Entity id = children.size() == 1 ? children.front() : 0;
          const auto *data = id ? ecm.Component<ContactSensorData>(id) : nullptr;
          if (rows >= limit) {
            overflow = true;
            out << "OVERFLOW\n";
            return false;
          }
          ++rows;
          out << stamp << '\t' << info.iterations << '\t' << dt << '\t'
              << topic << '\t' << model << '\t' << name(sensor, ecm) << '\t'
              << collision << '\t' << sensor << '\t' << id << '\t'
              << (data ? 1 : 0) << '\t'
              << (data ? data->Data().contact_size() : -1) << '\t';
          if (data) {
            bool first = true;
            for (const auto &hit : data->Data().contact()) {
              if (!first) out << ';';
              first = false;
              out << hit.collision1().id() << ':' << hit.collision2().id();
            }
          }
          const auto state = ecm.ComponentState(id, ContactSensorData::typeId);
          const char *value = state == gz::sim::ComponentState::OneTimeChange ? "ONE_TIME" :
              state == gz::sim::ComponentState::PeriodicChange ? "PERIODIC" : "NO_CHANGE";
          out << '\t' << (armIteration == info.iterations && armed.count(id) ? 1 : 0)
              << '\t' << value << '\t' << (late.count(id) ? 1 : 0) << '\n';
          return true;
        });
    out.flush();
  }
};
}
GZ_ADD_PLUGIN(smartdish::A14ProductionHealth, gz::sim::System,
              gz::sim::ISystemConfigure, gz::sim::ISystemPreUpdate,
              gz::sim::ISystemUpdate, gz::sim::ISystemPostUpdate)
GZ_ADD_PLUGIN_ALIAS(smartdish::A14ProductionHealth, "smartdish::A14ProductionHealth")
