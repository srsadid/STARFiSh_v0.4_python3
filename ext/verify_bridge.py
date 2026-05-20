import sys
import os

# Point this to the absolute path of your build folder
bridge_path = "/home/sadid/starfish/ext/build"
if bridge_path not in sys.path:
    sys.path.insert(0, bridge_path)

try:
    import crimson_starfish_bridge
    print("--- [Python] Module imported successfully ---")

    # Initialize the bridge
    # Parameters: hstep=100, alfi=0.5, delt=0.01
    bridge = crimson_starfish_bridge.CrimsonBridge(100, 0.5, 0.01)
    print("--- [Python] Bridge object created ---")

    # Trigger the XML loading logic
    # Use the repo-local single-resistor netlist fixture.
    xml_path = "/home/sadid/starfish/examples/baseline_netlist_from_xml/netlist_surfaces.xml"
    
    print("--- [Python] Calling bridge.load('{}') ---".format(xml_path))
    previous_cwd = os.getcwd()
    try:
        os.chdir(os.path.dirname(xml_path))
        bridge.load(xml_path, [0])
    finally:
        os.chdir(previous_cwd)
    print("--- [Python] Load call finished ---")

    coeffs = bridge.compute_implicit_coefficients(0, 1, 0.01, 0.01, 1.0e-5)
    print("--- [Python] Coefficients: dp_dq={}, Hop={} ---".format(coeffs[0], coeffs[1]))

except Exception as e:
    print("FAILED: {}".format(e))
