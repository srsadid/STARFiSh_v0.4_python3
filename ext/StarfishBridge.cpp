#include "NetlistCircuit.hxx"
#include <petscsys.h>  // Essential for PetscInitialize
#include <string>

class StarfishBridge {
public:
    StarfishBridge(int hstep, double alfi, double delt) {
        // 1. Initialize PETSc if it hasn't been started yet
        // This is a mechanical necessity for NetlistCircuit to function.
        PetscBool initialized;
        PetscInitialized(&initialized);
        if (!initialized) {
            PetscInitialize(NULL, NULL, NULL, NULL);
        }

        // 2. Use the 7-argument PUBLIC constructor
        // Signature: (hstep, surfaceIndex, LPNIndex, isRestart, alfi, delt, startStep)
        // i. hstep (int)
        // ii. indexOfThisNetlistLPN (int) -> We'll use 0 for the first/only circuit
        // iii. isRestarted (bool)          -> false
        // iv. alfi (double)               -> alfi
        // v. delt (double)               -> delt
        // vi. startingStep (int)          -> 0
        // We use 0 for surfaceIndex and LPNIndex as defaults for your coupling.
        m_circuit = boost::shared_ptr<NetlistCircuit>(
            new NetlistCircuit(hstep, 0, 0, false, alfi, delt, 0)
        );
    }

    void load(const std::string& xml_path) {
        // Ensure the filename is set before triggering the description build
        m_circuit->setNetlistXmlFileName(xml_path);
        m_circuit->createCircuitDescription();
    }

private:
    boost::shared_ptr<NetlistCircuit> m_circuit;
};