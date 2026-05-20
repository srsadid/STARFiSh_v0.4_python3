#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>  // Essential for handling std::string
#include <nanobind/stl/pair.h>
#include <nanobind/stl/vector.h>
#include "StarfishBridge.cpp"     // Ensure the path to your bridge class is correct

namespace nb = nanobind;

// This macro defines the entry point for the Python module.
// The first argument must match the project name in your CMakeLists.txt
NB_MODULE(crimson_starfish_bridge, m) {
    nb::class_<StarfishBridge>(m, "CrimsonBridge")
        .def(nb::init<int, double, double>())
        .def("load",
             nb::overload_cast<const std::string&>(&StarfishBridge::load))
        .def("load",
             nb::overload_cast<const std::string&, const std::vector<int>&>(&StarfishBridge::load))
        .def("compute_implicit_coefficients", &StarfishBridge::compute_implicit_coefficients)
        .def("update_state", &StarfishBridge::update_state)
        .def("finalize_timestep", &StarfishBridge::finalize_timestep);
}
