import os
import xml.etree.ElementTree as ET


DEFAULT_CRIMSON_ROOT = "/home/sadid/crimson/cfs_reg/CRIMSONFlowsolver"


class CrimsonNetlistAdapter(object):
    """
    STARFiSh-side adapter boundary for CRIMSON netlist support.

    STARFiSh remains the primary 1D Python solver. CRIMSON is treated as a
    helper boundary-condition manager. This lightweight implementation proves
    that STARFiSh can locate and read CRIMSON netlist input. The internals can
    later be replaced by a pybind/nanobind wrapper around CRIMSON's NetlistCircuit
    or NetlistBoundaryCondition APIs without changing STARFiSh's solver loop.
    """

    def __init__(self, netlist_xml=None, crimson_root=None):
        crimson_root = crimson_root or os.environ.get("CRIMSON_FLOWSOLVER_ROOT", DEFAULT_CRIMSON_ROOT)
        self.netlist_xml = netlist_xml or os.environ.get(
            "CRIMSON_NETLIST_XML",
            os.path.join(crimson_root, "netlist_surfaces.xml"),
        )

    def summary(self):
        tree = ET.parse(self.netlist_xml)
        root = tree.getroot()

        circuits = root.findall("circuit")
        components = root.findall(".//component")
        interface_nodes = [
            node.findtext("index", default="?")
            for node in root.findall(".//node")
            if (node.findtext("isAt3DInterface", default="false") or "").lower() == "true"
        ]

        return {
            "file": self.netlist_xml,
            "circuit_count": len(circuits),
            "component_count": len(components),
            "interface_nodes": interface_nodes,
        }

    def hello(self):
        info = self.summary()
        return (
            "hello from CRIMSON netlist: "
            "{file} | circuits={circuit_count} | components={component_count} | "
            "3D/1D interface nodes={interface_nodes}"
        ).format(**info)
