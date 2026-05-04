# CRIMSON Netlist Binding Plan

## Goal

Keep STARFiSh as the primary 1D solver and use CRIMSON only as a boundary-condition manager for netlist / LPN models.

The STARFiSh time loop should own:

- vessel grids and state arrays
- MacCormack / field update
- junction handling
- characteristic relations at open 1D boundaries

CRIMSON should own:

- netlist XML parsing
- circuit topology and component state
- Windkessel / RCR / more general LPN updates
- pressure-flow response at a boundary port

## First Presentation Demo

Current demo:

```bash
python demos/crimson_netlist_smoke.py
```

Expected output:

```text
hello from CRIMSON netlist: /home/sadid/crimson/cfs_reg/CRIMSONFlowsolver/netlist_surfaces.xml | circuits=1 | components=4 | 3D/1D interface nodes=['2']
next step: replace this XML probe with a nanobind/pybind wrapper around CRIMSON's NetlistCircuit/NetlistBoundaryCondition
```

This proves STARFiSh can locate and read CRIMSON netlist input. It does not yet call CRIMSON C++.

## Binding Target

For the first real C++ binding, target `NetlistCircuit` before the full CRIMSON solver.

Relevant CRIMSON methods in `flowsolver/src/NetlistCircuit.hxx`:

- `initialiseCircuit()`
- `setPressureAndFlowPointers(double* pressurePointer, double* flowPointer)`
- `initialiseAtStartOfTimestep()`
- `computeImplicitCoefficients(...)`
- `updateLPN(...)`
- `finalizeLPNAtEndOfTimestep()`
- `computeAndGetFlowOrPressureToGiveToZeroDDomainReplacement()`

The important design point is that STARFiSh should pass boundary pressure/flow values into the netlist object and receive the updated boundary response back.

## Proposed Python API

The Python-facing object should be small:

```python
bc = CrimsonNetlistBoundary(
    netlist_xml="/path/to/netlist_surfaces.xml",
    surface_index=1,
    dt=dt,
)

bc.initialize()

for n, t in enumerate(time):
    pressure, flow = bc.step(
        timestep=n,
        time=t,
        pressure_1d=pressure_at_boundary,
        flow_1d=flow_at_boundary,
    )
```

The STARFiSh solver remains responsible for solving the 1D boundary compatibility equation. The CRIMSON netlist object supplies the circuit relation. For a robust implementation this will likely become a small nonlinear solve at each boundary:

```text
1D characteristic relation + CRIMSON netlist pressure-flow relation = boundary pressure and flow
```

## nanobind vs pybind11

Either works. For a compact modern binding, `nanobind` is a good choice. `pybind11` may be easier if CRIMSON already has older CMake patterns or developers are more familiar with it.

The first compiled extension should expose only a minimal wrapper class:

- construct circuit
- initialize circuit
- set/get interface pressure and flow
- advance one timestep
- print netlist metadata

Do not bind the whole CRIMSON solver.

## Implementation Stages

1. XML smoke test
   - Done in `UtilityLib/crimsonNetlistAdapter.py`.
   - Good enough for a presentation screenshot.

2. C++ hello binding
   - Build a Python extension that links against CRIMSON C++.
   - Expose a function like `hello_from_crimson_netlist()`.
   - Return the netlist filename, circuit count, or surface index.

3. Netlist object binding
   - Wrap `NetlistCircuit`.
   - Initialize it from CRIMSON's existing `netlist_surfaces.xml`.
   - Step it with simple prescribed pressure/flow values.

4. STARFiSh boundary adapter
   - Add a STARFiSh boundary condition class that calls the Python wrapper.
   - Start with one terminal vessel.
   - Keep existing STARFiSh boundary conditions intact while testing.

5. Coupled boundary solve
   - Combine the 1D characteristic boundary equation with the netlist response.
   - Replace ReflectionCoefficient/Windkessel test outlets one at a time.

## Risks

- CRIMSON netlist code depends on PETSc and existing CRIMSON global state.
- Some netlist classes expect files with hardcoded names such as `netlist_surfaces.xml`.
- `NetlistBoundaryCondition` is tied to CRIMSON's multidomain boundary manager, so it may be heavier than needed for STARFiSh.
- `NetlistCircuit` is probably the cleaner first binding surface, but it may still need a small C++ facade to hide PETSc and pointer ownership.

## Recommended C++ Facade

Create a small C++ class on the CRIMSON side:

```cpp
class StarfishCrimsonNetlistBoundary {
public:
    StarfishCrimsonNetlistBoundary(std::string netlistXml, int surfaceIndex, double dt);
    void initialize();
    std::pair<double, double> step(int timestep, double time, double pressure1d, double flow1d);
    std::string summary() const;
};
```

Bind this facade to Python instead of directly exposing all CRIMSON internals. That keeps Python ownership simple and gives STARFiSh a stable boundary-condition API.
