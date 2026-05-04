#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>  // Essential for handling std::string
#include "StarfishBridge.cpp"     // Ensure the path to your bridge class is correct

namespace nb = nanobind;

// This macro defines the entry point for the Python module.
// The first argument must match the project name in your CMakeLists.txt
NB_MODULE(crimson_starfish_bridge, m) {
    nb::class_<StarfishBridge>(m, "CrimsonBridge")
        .def(nb::init<int, double, double>())
        .def("load", &StarfishBridge::load);
}