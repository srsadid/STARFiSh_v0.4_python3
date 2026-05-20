#include "NetlistCircuit.hxx"
#include "NetlistXmlReader.hxx"

#include <petscsys.h>

#include <algorithm>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include <boost/shared_ptr.hpp>

class StarfishBridge {
public:
    StarfishBridge(int hstep, double alfi, double delt)
        : m_hstep(hstep),
          m_alfi(alfi),
          m_delt(delt),
          m_loaded(false),
          m_timestepStarted(false),
          m_timestepFinalized(false),
          m_currentTimestep(-1) {
        PetscBool initialized;
        PetscInitialized(&initialized);
        if (!initialized) {
            PetscInitialize(NULL, NULL, NULL, NULL);
        }
    }

    ~StarfishBridge() {
        NetlistXmlReader::Term();
        NetlistDownstreamXmlReader::Term();
    }

    void load(const std::string& xml_path) {
        std::vector<int> surface_ids;
        load(xml_path, surface_ids);
    }

    void load(const std::string& xml_path, const std::vector<int>& surface_ids) {
        if (m_loaded) {
            return;
        }

        m_xmlPath = xml_path;

        std::vector<int> sorted_surface_ids = surface_ids;
        std::sort(sorted_surface_ids.begin(), sorted_surface_ids.end());
        sorted_surface_ids.erase(
            std::unique(sorted_surface_ids.begin(), sorted_surface_ids.end()),
            sorted_surface_ids.end());

        for (std::vector<int>::const_iterator surface_id = sorted_surface_ids.begin();
             surface_id != sorted_surface_ids.end();
             ++surface_id) {
            create_surface_if_needed(*surface_id);
        }

        m_loaded = true;
    }

    std::pair<double, double> compute_implicit_coefficients(int surface_id,
                                                            int timestep,
                                                            double time,
                                                            double dt,
                                                            double flow) {
        ensure_loaded();
        ensure_dt_matches(dt);

        SurfaceState& state = get_surface(surface_id);
        begin_timestep_if_needed(timestep);

        state.flow = flow;
        double alfi_delt = m_alfi * m_delt;
        return state.circuit->computeImplicitCoefficients(timestep, time, alfi_delt);
    }

    void update_state(int surface_id,
                      int timestep,
                      double /*time*/,
                      double dt,
                      double pressure,
                      double flow) {
        ensure_loaded();
        ensure_dt_matches(dt);

        SurfaceState& state = get_surface(surface_id);
        begin_timestep_if_needed(timestep);

        state.pressure = pressure;
        state.flow = flow;
        state.circuit->updateLPN(timestep);
    }

    void finalize_timestep(int timestep) {
        ensure_loaded();
        if (m_timestepFinalized && m_currentTimestep == timestep) {
            return;
        }

        for (std::map<int, SurfaceState>::iterator entry = m_surfaces.begin();
             entry != m_surfaces.end();
             ++entry) {
            entry->second.circuit->finalizeLPNAtEndOfTimestep();
        }

        m_timestepFinalized = true;
    }

private:
    struct SurfaceState {
        SurfaceState()
            : pressure(0.0),
              flow(0.0) {
        }

        double pressure;
        double flow;
        boost::shared_ptr<NetlistCircuit> circuit;
    };

    void ensure_loaded() const {
        if (!m_loaded) {
            throw std::runtime_error("StarfishBridge.load(xml_path) must be called before using the netlist.");
        }
    }

    void ensure_dt_matches(double dt) const {
        if (dt != m_delt) {
            std::stringstream message;
            message << "StarfishBridge was constructed with delt=" << m_delt
                    << " but received dt=" << dt << ".";
            throw std::runtime_error(message.str());
        }
    }

    void create_surface_if_needed(int surface_id) {
        if (m_surfaces.find(surface_id) != m_surfaces.end()) {
            return;
        }

        std::pair<std::map<int, SurfaceState>::iterator, bool> insertion =
            m_surfaces.insert(std::make_pair(surface_id, SurfaceState()));
        SurfaceState& state = insertion.first->second;

        int netlist_index = static_cast<int>(m_surfaces.size()) - 1;
        state.circuit = boost::shared_ptr<NetlistCircuit>(
            new NetlistCircuit(m_hstep, surface_id, netlist_index, false, m_alfi, m_delt, 0));

        state.circuit->setNetlistXmlFileName(m_xmlPath);
        state.circuit->setPressureAndFlowPointers(&state.pressure, &state.flow);
        state.circuit->createCircuitDescription();
        state.circuit->closeAllDiodes();
        state.circuit->detectWhetherClosedDiodesStopAllFlowAt3DInterface();
        state.circuit->initialiseCircuit();

        if (m_timestepStarted) {
            state.circuit->initialiseAtStartOfTimestep();
        }
    }

    SurfaceState& get_surface(int surface_id) {
        create_surface_if_needed(surface_id);
        return m_surfaces.at(surface_id);
    }

    void begin_timestep_if_needed(int timestep) {
        if (m_timestepStarted && m_currentTimestep == timestep) {
            return;
        }

        for (std::map<int, SurfaceState>::iterator entry = m_surfaces.begin();
             entry != m_surfaces.end();
             ++entry) {
            entry->second.circuit->initialiseAtStartOfTimestep();
        }

        m_currentTimestep = timestep;
        m_timestepStarted = true;
        m_timestepFinalized = false;
    }

    int m_hstep;
    double m_alfi;
    double m_delt;
    std::string m_xmlPath;
    std::map<int, SurfaceState> m_surfaces;
    bool m_loaded;
    bool m_timestepStarted;
    bool m_timestepFinalized;
    int m_currentTimestep;
};
