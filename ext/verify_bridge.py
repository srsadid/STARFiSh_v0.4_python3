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
    # Use the absolute path to your netlist file
    xml_path = "/home/sadid/temp/optimized/netlist_surfaces.xml"
    
    print("--- [Python] Calling bridge.load('{}') ---".format(xml_path))
    bridge.load(xml_path)
    print("--- [Python] Load call finished ---")

except Exception as e:
    print("FAILED: {}".format(e))