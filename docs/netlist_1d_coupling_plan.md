# Netlist 1D Coupling Plan

This note defines the first coupling target between the STARFiSh 1D solver and
the CRIMSON netlist boundary-condition machinery.

The first user-facing boundary condition should be named simply:

```xml
<_Netlist>
  <surfaceId>0</surfaceId>
</_Netlist>
```

The real netlist circuit description is not parsed by STARFiSh. It remains a
CRIMSON netlist input file and is handled by CRIMSON's own netlist XML reader.
The STARFiSh XML only maps a 1D vessel boundary to a netlist surface. The
netlist file name is intentionally fixed:

```text
netlist_surfaces.xml
```

and that file must live in the same case directory as STARFiSh `input.xml`.

For early testing, `_Netlist` may also support a temporary constant-coefficient
mode:

```xml
<_Netlist>
  <surfaceId>0</surfaceId>
  <Rtilde unit="Pa s m-3">133320000.0</Rtilde>
  <S unit="Pa">0.0</S>
  <flowSign>1</flowSign>
</_Netlist>
```

This fake mode lets us verify the 1D characteristic coupling before calling the
C++ netlist.

Internally, the coupling law is the Robin pressure-flow condition:

```text
P = Rtilde * Q + S
```

This matches the CRIMSON netlist interface form:

```text
P = Q * R~ + S
```

where:

- `P` is the interface pressure.
- `Q` is the interface flow.
- `Rtilde` / `R~` / `dp_dq` is the effective pressure-flow slope.
- `S` / `Hop` is the pressure shift from history, sources, capacitors, and
  other netlist state.

## Current Implementation Map

The coupling now has three layers:

```text
STARFiSh XML + Type 2 BC
  -> Python interface/manager
  -> CRIMSON C++ netlist bridge
```

The main rule is that STARFiSh owns the 1D solver and characteristic update,
while CRIMSON owns the netlist circuit solve.

### Files Added or Extended

```text
NetworkLib/classBoundaryConditions.py
```

Adds the STARFiSh Type 2 boundary condition:

```python
class Netlist(BoundaryConditionType2)
```

Responsibilities:

- receives XML fields already parsed by STARFiSh:
  `surfaceId`, plus optional `flowSign`, `Rtilde`, `S`
- registers the boundary with `NetlistBoundaryManager`
- creates `NetlistBoundaryInterface`
- delegates each solver boundary call to the interface layer

Important methods:

```python
Netlist.initialize()
Netlist.setPosition(position)
Netlist.funcPos0(...)
Netlist.funcPos1(...)
```

`funcPos0` is the proximal/inlet-side handler and `funcPos1` is the
distal/outlet-side handler. Both call the same interface object; the interface
uses `position` to select the correct characteristic direction.

```text
NetworkLib/netlistInterface.py
```

Owns the 1D mathematical coupling.

Important function:

```python
solve_robin_characteristic(
    position,
    omega_known,
    R,
    P,
    Q,
    dp_dq,
    hop,
    flow_sign=1.0)
```

This solves the unknown characteristic from:

```text
P_new = dp_dq * (flow_sign * Q_new) + hop
```

and:

```text
[dP, dQ]^T = R_char * omega
```

Important class:

```python
class NetlistBoundaryInterface
```

Responsibilities:

- asks the manager for `(dp_dq, Hop)`
- solves the unknown characteristic
- computes `du = [dP, dQ]`
- records final interface pressure/flow back into the manager

Important method:

```python
NetlistBoundaryInterface.solve(...)
```

This is the main call path from STARFiSh into the netlist coupling.

```text
NetworkLib/netlistManager.py
```

Owns boundary registration and chooses where coefficients come from.

Important class:

```python
class NetlistBoundaryManager
```

Responsibilities:

- stores all registered netlist boundaries by `surfaceId`
- owns one global netlist file for the whole case:

  ```text
  <case directory>/netlist_surfaces.xml
  ```

  This matches CRIMSON's `numNetlistLPNSrfs` / `indicesOfNetlistSurfaces(k)`
  model: one file contains all outlet circuits, while each STARFiSh boundary
  only says which `surfaceId` it maps to.

- supports fake constant mode for quick tests:

  ```text
  Rtilde != None -> return (Rtilde, S)
  ```

- supports real CRIMSON mode:

  ```text
  Rtilde == None -> call CrimsonNetlistAdapter
  ```

- records final `(P, Q)` after the 1D characteristic solve
- forwards final state to CRIMSON in real mode
- finalizes the one loaded adapter once per timestep when called

Important methods:

```python
register_boundary(...)
compute_coefficients(...)
record_boundary_state(...)
finalize_timestep(...)
```

```text
UtilityLib/crimsonNetlistAdapter.py
```

Python adapter around the compiled CRIMSON bridge.

Important class:

```python
class CrimsonNetlistAdapter
```

Responsibilities:

- imports the compiled module `crimson_starfish_bridge`
- constructs `CrimsonBridge(hstep, alfi, delt)`
- loads the CRIMSON netlist XML
- calls CRIMSON for `(dp_dq, Hop)`
- pushes final `(P, Q)` back to CRIMSON

Important methods:

```python
load(dt=None)
compute_implicit_coefficients(surface_id, timestep, time, dt, flow)
update_state(surface_id, timestep, time, dt, pressure, flow)
finalize_timestep(timestep)
```

Current practical note:

CRIMSON's XML reader still assumes `netlist_surfaces.xml` can be opened from
the current working directory. The adapter temporarily changes directory to the
XML file directory during `load()` so local case folders work.

```text
ext/StarfishBridge.cpp
```

C++ bridge between Python and CRIMSON's `NetlistCircuit`.

Important class:

```cpp
class StarfishBridge
```

Responsibilities:

- initializes PETSc if needed
- owns one `NetlistCircuit`
- owns scalar pressure/flow values whose addresses are passed into CRIMSON
- loads the CRIMSON netlist file
- returns CRIMSON's affine pressure-flow law:

  ```text
  (dp_dq, Hop)
  ```

Important methods:

```cpp
void load(const std::string& xml_path);
std::pair<double, double> compute_implicit_coefficients(
    int timestep,
    double time,
    double dt,
    double flow);
void update_state(
    int timestep,
    double time,
    double dt,
    double pressure,
    double flow);
void finalize_timestep(int timestep);
```

Current call sequence inside `load()`:

```cpp
setNetlistXmlFileName(xml_path)
setPressureAndFlowPointers(&pressure, &flow)
createCircuitDescription()
closeAllDiodes()
detectWhetherClosedDiodesStopAllFlowAt3DInterface()
initialiseCircuit()
```

```text
ext/bindings.cpp
```

Nanobind module definition.

Python-visible class:

```python
crimson_starfish_bridge.CrimsonBridge
```

Bound methods:

```python
load(...)
compute_implicit_coefficients(...)
update_state(...)
finalize_timestep(...)
```

```text
ext/verify_bridge.py
```

Small verification script. It loads:

```text
examples/baseline_netlist_from_xml/netlist_surfaces.xml
```

and checks that the bridge returns coefficients from CRIMSON.

```text
UtilityLib/networkXml043.py
UtilityLib/constants.py
```

XML registration layer.

Responsibilities:

- make `Netlist` and `_Netlist` visible in STARFiSh `input.xml`
- define fields:

  ```text
  surfaceId
  flowSign  optional, defaults to 1
  Rtilde    optional, defaults to None
  S         optional, defaults to 0
  ```

`Rtilde` and `S` are allowed to be `None` so the same XML structure can run in
real CRIMSON mode.

```text
NetworkLib/classVascularNetwork.py
```

Currently has a small compatibility update so fake constant `_Netlist` cases
can participate in resistance estimation when `Rtilde` is provided.

Open cleanup:

Real adapter mode with `Rtilde=None` still cannot provide an initial resistance
estimate to STARFiSh during initialization. The solver can run, but STARFiSh
prints its fallback resistance message. A later cleanup should let the manager
query CRIMSON once during initialization or provide an optional initialization
resistance.

## Data Flow Schematic

Current implemented flow:

```text
STARFiSh input.xml
  |
  |  vesselId, boundary position, surfaceId,
  |  flowSign, optional Rtilde/S
  v
classBoundaryConditions.Netlist
  |
  |  P, Q, known omega, R_char, n, dt
  v
NetworkLib.netlistInterface.NetlistBoundaryInterface
  |
  |  asks for coefficients:
  |  surfaceId, timestep, time, dt, pressure, signed flow
  v
NetworkLib.netlistManager.NetlistBoundaryManager
  |        |
  |        | fake mode: Rtilde/S from input.xml
  |        |
  |        | real mode: call Python adapter
  v
UtilityLib.crimsonNetlistAdapter.CrimsonNetlistAdapter
  |
  |  import nanobind module and call bridge
  v
ext.crimson_starfish_bridge.CrimsonBridge
  |
  |  C++ StarfishBridge -> CRIMSON NetlistCircuit
  |
  |  CRIMSON parses netlist_surfaces.xml and solves circuit
  v
dp_dq, Hop
  |
  v
NetlistBoundaryInterface solves unknown characteristic
  |
  |  du = [dP, dQ]
  v
P^{n+1}, Q^{n+1}
  |
NetlistBoundaryManager records final interface state
  |
  |  real mode: queue final P/Q by surfaceId
  v
class1DflowSolver finishes all numerical objects for timestep n
  |
  |  finalizeNetlistTimestep(n)
  v
NetlistBoundaryManager pushes all queued final P/Q values
  |
  |  adapter.update_state(...) for every pending surface
  |  adapter.finalize_timestep(n) once
  v
CRIMSON advances/finalizes the global netlist state once for timestep n
```

The important separation is:

```text
STARFiSh XML:
  maps the 1D boundary to a netlist surface.

CRIMSON netlist XML:
  defines the actual circuit.

Python interface:
  translates between 1D characteristic variables and CRIMSON's P/Q law.
```

The end-of-timestep split is intentional. Each 1D boundary solves its own
characteristic problem and records the final interface state, but no boundary
condition object should independently advance the global netlist. The flow
solver is the only place that knows all boundary objects have run for timestep
`n`, so it calls:

```python
FlowSolver.finalizeNetlistTimestep(n)
```

That call flushes every pending surface update to the one shared adapter and
then finalizes CRIMSON once. This mirrors the CRIMSON pattern:

```text
compute interface law during the flow solve
collect final interface flow/pressure
update/finalize the netlist once at the end of the timestep
```

## Milestone 1: XML Visibility

Goal: prove the solver can read a `Netlist` boundary condition from `input.xml`.

Implementation steps:

1. Add `Netlist` and `_Netlist` to `UtilityLib/networkXml043.py`.
2. Register XML fields:

   ```python
   ["surfaceId", "flowSign", "Rtilde", "S"]
   ```

   `flowSign`, `Rtilde`, and `S` are optional for `_Netlist`.
   In the real coupled mode, omit `Rtilde` and `S`; the CRIMSON netlist wrapper
   provides them as `(dp_dq, Hop)`.

3. Add a skeletal Type 2 class in `NetworkLib/classBoundaryConditions.py`:

   ```python
   class Netlist(BoundaryConditionType2):
       def __init__(self):
           self.type = 2
           self.surfaceId = None
           self.networkDirectory = None
           self.flowSign = 1.0
           self.Rtilde = None
           self.S = 0.0
   ```

4. Load a case and verify that the object is created with the expected parsed
   values. This milestone does not need to solve the boundary yet.

## Milestone 2: Single-Tube Robin Behavior

Goal: make `_Netlist` behave like `_Resistance` for one outlet.

Use the existing baseline case:

```text
examples/baseline_resistance/input.xml
```

Duplicate it, then replace:

```xml
<_Resistance>
  <Rc unit="Pa s m-3">133320000.0</Rc>
</_Resistance>
```

with:

```xml
<_Netlist>
  <surfaceId>0</surfaceId>
  <Rtilde unit="Pa s m-3">133320000.0</Rtilde>
  <S unit="Pa">0.0</S>
</_Netlist>
```

Expected result:

```text
P_out and Q_out match the _Resistance case.
```

This validates the 1D characteristic coupling before adding any C++ netlist
code.

## Boundary Math

At a 1D boundary, one characteristic comes from the vessel interior and the
other characteristic is unknown. The Type 2 boundary condition must solve:

```text
1D characteristic compatibility
P = Rtilde * Q + S
```

The characteristic transform gives:

```text
[dP, dQ]^T = R_char * [omega_known, omega_unknown]^T
```

Since `P = P_old + dP` and `Q = Q_old + dQ`, the unknown characteristic can be
solved directly for the affine netlist law. No Newton solve is needed for this
first Robin-style interface.

Newton or finite-difference Jacobians are only needed if the 0D side exposes a
nonlinear residual directly:

```text
F(P, Q, state) = 0
```

instead of exposing:

```text
P = Rtilde * Q + S
```

## Milestone 3: Python Manager Layer

Even for a single tube, add a manager abstraction before calling C++ directly.

Recommended file split:

```text
NetworkLib/classBoundaryConditions.py
  Netlist
    Thin STARFiSh Type 2 caller.

NetworkLib/netlistInterface.py
  NetlistBoundaryInterface
    Owns the 1D characteristic solve and the Robin law.

NetworkLib/netlistManager.py
  NetlistBoundaryManager
    Owns surface registration, fake-vs-C++ adapter selection,
    coefficient calls, and timestep finalization.

ext / compiled binding
  Owns the actual C++ CRIMSON netlist wrapper.
```

The `Netlist` class in `classBoundaryConditions.py` should remain small:

```python
class Netlist(BoundaryConditionType2):
    def __call__(self, omega_known, du_prescribed, R, L, nmem, n, dt, P, Q, A, Z1, Z2):
        return self.interface.solve(
            omega_known=omega_known,
            R=R,
            nmem=nmem,
            n=n,
            dt=dt,
            P=P,
            Q=Q,
            A=A,
            Z1=Z1,
            Z2=Z2,
        )
```

The interface layer owns the characteristic algebra:

```python
class NetlistBoundaryInterface:
    def solve(self, omega_known, R, nmem, n, dt, P, Q, A, Z1, Z2):
        Rtilde, S = self.manager.compute_coefficients(
            surface_id=self.surface_id,
            timestep=n,
            time=n * dt,
            dt=dt,
            pressure=P,
            flow=self.flow_sign * Q,
        )

        omega_vector = self.solve_unknown_characteristic(
            position=self.position,
            omega_known=omega_known,
            R=R,
            P=P,
            Q=Q,
            Rtilde=Rtilde,
            S=S,
        )

        du = np.dot(R, omega_vector)
        P_new = P + du[0]
        Q_new = Q + du[1]
        self.manager.record_boundary_state(
            self.surface_id,
            n,
            n * dt,
            dt,
            P_new,
            self.flow_sign * Q_new,
        )
        return du, self.compute_dq_in_out(omega_vector, R)
```

Manager-level conceptual API:

```python
class NetlistBoundaryManager:
    def set_netlist_file(self, netlist_file):
        ...

    def register_boundary(self, surface_id, vessel_id, position):
        ...

    def compute_coefficients(self, surface_id, timestep, time, dt, pressure, flow):
        return Rtilde, S

    def record_boundary_state(self, surface_id, timestep, time, dt, pressure, flow):
        ...

    def finalize_timestep(self, timestep):
        ...
```

For the first version, the manager can return constants from XML:

```text
Rtilde, S
```

Later, the same manager calls the CRIMSON C++ wrapper.

The reason to add this layer early is that real netlists can couple multiple
surfaces. Each boundary condition should not independently own or finalize a
separate netlist.

## Current Python-Side Roles

The current code is intentionally split into four small roles.

```text
NetworkLib/classBoundaryConditions.py
```

This is the STARFiSh entry point. `Netlist` is a Type 2 boundary condition, but
it should stay thin. Its job is to receive parsed XML values, identify the
vessel end (`position`), register the boundary once, and call the interface
solver every time STARFiSh evaluates that boundary.

```text
NetworkLib/netlistInterface.py
```

This owns the numerical 1D/0D interface math. It asks for `(dp_dq, Hop)`, solves
the unknown characteristic, returns `du = [dP, dQ]`, and records the final
interface state. This is where any future nonlinear characteristic solve should
live if the CRIMSON side exposes a residual instead of an affine law.

```text
NetworkLib/netlistManager.py
```

This owns case-level netlist state. There is one global netlist file,
`netlist_surfaces.xml`, and many possible STARFiSh boundaries mapped by
`surfaceId`. The manager registers those mappings, chooses fake constant mode
versus real CRIMSON mode, queues final boundary states, and finalizes the
adapter once per timestep.

The manager is deliberately different from the adapter:

```text
manager = STARFiSh coupling coordinator
adapter = thin Python wrapper over compiled C++
```

```text
UtilityLib/crimsonNetlistAdapter.py
```

This file should contain no 1D solver logic. It imports the compiled
`crimson_starfish_bridge` module, loads the fixed CRIMSON XML file, asks C++ for
coefficients, pushes final pressure/flow values, and calls finalization. It is
the only Python file that should know about the compiled binding details.

```text
SolverLib/class1DflowSolver.py
```

This owns timestep-level finalization. After every numerical object has run for
a timestep, it calls:

```python
get_default_netlist_manager().finalize_timestep(n)
```

That is the point where pending surface states become CRIMSON netlist state.

## Milestone 4: Single-Surface C++ Bridge

Once `_Netlist` matches `_Resistance`, replace the fake manager coefficients
with a C++ bridge.

Minimum bridge API:

```python
load()
compute_implicit_coefficients(surface_id, timestep, time, dt, q_current)
update_state(surface_id, timestep, time, dt, p_final, q_final)
finalize_timestep(timestep)
```

Minimum returned data:

```text
Rtilde, S
```

The STARFiSh boundary condition should not care whether these values came from
XML constants, a fake Python object, or the CRIMSON netlist solver.

In real mode, the CRIMSON netlist XML file is fixed to:

```text
netlist_surfaces.xml
```

in the same directory as STARFiSh `input.xml`.

STARFiSh should not parse the circuit topology, components, prescribed nodal
pressures, component flows, diode states, or capacitor histories. That logic
belongs inside CRIMSON's netlist code.

Current C++ bridge status:

```text
ext/StarfishBridge.cpp
```

is the active build target for STARFiSh. It is intentionally kept in the
STARFiSh `ext/` tree so this project can be built and tested without modifying
CRIMSON's SCons build chain. The current bridge stores one `SurfaceState` per
STARFiSh `surfaceId` and uses one direct CRIMSON `NetlistCircuit` per surface:

```text
current:
  one global netlist_surfaces.xml
  many registered surface states
  surfaceId -> direct NetlistCircuit mapping
  coefficient lookup per surface
  delayed global finalization after all surfaces update
```

The important remaining caveat is that `surfaceId` is used as the STARFiSh-side
surface key and CRIMSON output surface index, while the CRIMSON XML circuit is
selected by construction order. The manager passes sorted registered surface IDs
at load time so the mapping is deterministic. We still need explicit validation
against real CRIMSON `indicesOfNetlistSurfaces` cases.

## CRIMSON Netlist File Ownership

The relevant CRIMSON source directory is:

```text
/home/sadid/crimson/cfs_reg/CRIMSONFlowsolver/flowsolver/src/
```

The STARFiSh side now follows the CRIMSON convention directly. The input file
is always named:

```text
netlist_surfaces.xml
```

and it must be placed next to STARFiSh `input.xml` in the case directory.
STARFiSh should not accept per-boundary netlist filenames in `input.xml`; that
keeps case layout predictable and avoids path ambiguity.

The STARFiSh `input.xml` should only contain:

```text
surfaceId
flowSign
```

The CRIMSON netlist file contains the actual circuit.

## CRIMSON Files to Wrap

Core netlist solver files:

```text
NetlistCircuit.hxx
NetlistCircuit.cxx
CircuitData.hxx
CircuitData.cxx
CircuitComponent.hxx
CircuitComponent.cxx
CircuitPressureNode.hxx
CircuitPressureNode.cxx
NetlistXmlReader.hxx
NetlistXmlReader.cxx
datatypesInCpp.hxx
fileReaders.hxx
fileReaders.cxx
fileWriters.hxx
fileWriters.cxx
indexShifters.hxx
customCRIMSONContainers.hxx
debuggingToolsForCpp.hxx
```

CRIMSON boundary-condition wrapper layer:

```text
NetlistBoundaryCondition.hxx
NetlistBoundaryCondition.cxx
AbstractBoundaryCondition.hxx
AbstractBoundaryCondition.cxx
BoundaryConditionFactory.hxx
BoundaryConditionFactory.cxx
BoundaryConditionManager.hxx
BoundaryConditionManager.cxx
FortranBoundaryDataPointerManager.hxx
FortranBoundaryDataPointerManager.cxx
```

Optional advanced modes:

```text
NetlistBoundaryCircuitWhenDownstreamCircuitsExist.hxx
NetlistBoundaryCircuitWhenDownstreamCircuitsExist.cxx
NetlistClosedLoopDownstreamCircuit.hxx
NetlistClosedLoopDownstreamCircuit.cxx
ClosedLoopBoundaryConditionSubsection.hxx
ClosedLoopBoundaryConditionSubsection.cxx
Netlist3DDomainReplacement.hxx
Netlist3DDomainReplacement.cxx
NetlistZeroDDomainCircuit.hxx
NetlistZeroDDomainCircuit.cxx
```

The ideal long-term path is to use the CRIMSON boundary-condition wrapper layer
through `NetlistBoundaryCondition` or `BoundaryConditionFactory`, because that
is closest to how CRIMSON already computes `(dp_dq, Hop)` for the higher
dimensional solver.

Current practical path:

```text
ext/StarfishBridge.cpp -> NetlistCircuit directly
```

We tried the wrapper-layer route first, but importing the rebuilt Python 3
extension failed with an unresolved `PyString_FromString` symbol. That symbol
comes from older CRIMSON Python-control-system code pulled in by the fuller
boundary-condition wrapper path. Until that is isolated or ported cleanly, the
active bridge uses `NetlistCircuit` directly while preserving the same Python
API and timestep flow.

## C++ Calling Shape

Minimal direct `NetlistCircuit` sequence:

```cpp
NetlistCircuit circuit(
    hstep,
    surfaceIndex,
    netlistIndex,
    restarted,
    alfi,
    delt,
    startingTimestepIndex);

circuit.setPointersToBoundaryPressuresAndFlows(&pressure, &flow, 1);
circuit.createCircuitDescription();
circuit.closeAllDiodes();
circuit.detectWhetherClosedDiodesStopAllFlowAt3DInterface();
circuit.initialiseCircuit();

circuit.initialiseAtStartOfTimestep();
auto coeffs = circuit.computeImplicitCoefficients(
    timestepNumber,
    timeAtNplus1,
    alfi_delt);
circuit.updateLPN(timestepNumber);
circuit.finalizeLPNAtEndOfTimestep();
```

Preferred boundary-condition wrapper sequence:

```cpp
NetlistBoundaryCondition bc(
    surfaceIndex,
    hstep,
    delt,
    alfi,
    startingTimestepIndex,
    maxsurf,
    nstep,
    downstreamSubcircuits);

bc.setPressureAndFlowPointers(&pressure, &flow);
bc.initialiseModel();

bc.initialiseAtStartOfTimestep();
bc.computeImplicitCoeff_solve(timestepNumber);
double Rtilde = bc.getdp_dq();
double S = bc.getHop();
bc.updateLPN(timestepNumber);
bc.finaliseAtEndOfTimestep();
```

The Python adapter hides the C++ sequence behind a small API:

```python
class CrimsonNetlistAdapter:
    def load(self, dt=None):
        ...

    def compute_implicit_coefficients(self, surface_id, timestep, time, dt, flow):
        return dp_dq, hop

    def update_state(self, surface_id, timestep, time, dt, pressure, flow):
        ...

    def finalize_timestep(self, timestep):
        ...
```

## Existing C++ Starting Point

Current prototype files:

```text
/home/sadid/crimson/cfs_reg/CRIMSONFlowsolver/flowsolver/src/Netlist1DWrapper.hxx
/home/sadid/crimson/cfs_reg/CRIMSONFlowsolver/flowsolver/src/Netlist1DWrapper.cxx
```

These files are useful design references, but they do not have to become the
active wrapper. For this project, the cleaner build path is:

```text
STARFiSh owns:
  ext/StarfishBridge.cpp
  ext/bindings.cpp
  ext/CMakeLists.txt

CRIMSON source provides:
  netlist classes included/linked by the STARFiSh extension
```

This avoids adding experimental 1D code to CRIMSON's main source tree and avoids
threading a prototype through CRIMSON's SCons build. If `Netlist1DWrapper` has a
better internal call sequence, copy the idea into `ext/StarfishBridge.cpp`
rather than making STARFiSh depend on that file directly.

Current wrapper shape:

```cpp
std::pair<double, double> computeImplicitCoefficients(
    int surfaceIndex,
    int timestep,
    double time,
    double dt,
    double flow);

void updateState(
    int surfaceIndex,
    int timestep,
    double time,
    double dt,
    double pressure,
    double flow);
```

This is aligned with the 1D coupling plan because it already returns:

```text
(Rtilde, S) == (dp_dq, Hop)
```

The useful ideas to borrow are:

- Store one `SurfaceState` per CRIMSON surface.
- Give each state its own pressure and flow scalar whose addresses are passed to
  `NetlistBoundaryCondition`.
- Use `BoundaryConditionFactory` / `NetlistBoundaryCondition`, because that is
  closest to the real CRIMSON 3D path.
- Begin a timestep once, compute coefficients as needed, then finalize once.

Important limitations to address before multi-surface use:

- `updateState()` finalizes the timestep immediately. For multiple surfaces,
  all final `P/Q` values must be pushed first, then the netlist should finalize
  once.
- `ensureDtMatches_()` requires `dt == config_.delt`. STARFiSh may adapt `dt`
  depending on CFL, so either the wrapper must support timestep-specific `dt`
  or the 1D solver must run with a fixed compatible timestep.
- The wrapper currently exposes scalar `(dp_dq, Hop)` per surface. That is fine
  for the first diagonal coupling. A later multi-surface version may need:

  ```text
  P_i = sum_j M_ij Q_j + S_i
  ```

- Sign convention must be verified. We need a clear rule for whether positive
  STARFiSh `Q` means flow leaving the 1D domain or entering the netlist.
- Netlist file discovery is deliberately fixed. The STARFiSh case directory
  must provide `netlist_surfaces.xml` next to `input.xml`.

Recommended bridge shape for the next implementation:

```cpp
class StarfishBridge {
public:
    void load(const std::string& netlist_xml_path,
              const std::vector<int>& surface_ids);

    std::pair<double, double> compute_implicit_coefficients(
        int surface_id,
        int timestep,
        double time,
        double dt,
        double flow);

    void update_state(
        int surface_id,
        int timestep,
        double time,
        double dt,
        double pressure,
        double flow);

    void finalize_timestep(int timestep);

private:
    struct SurfaceState {
        double pressure;
        double flow;
        boost::shared_ptr<NetlistBoundaryCondition> bc;
    };

    std::map<int, SurfaceState> surfaces_;
};
```

The Python API can remain stable while the C++ implementation changes.

## Milestone 5: Multi-Surface Coupling

After the single-tube case works:

1. Map each STARFiSh boundary to a CRIMSON `surfaceId`.
2. Validate surface ordering and sign conventions.
3. Compute coefficients for all surfaces together.
4. Solve each 1D boundary using the current diagonal law:

   ```text
   P_i = Rtilde_i * Q_i + S_i
   ```

5. Update all final interface `P/Q` values.
6. Finalize the netlist once per timestep.

The first multi-surface implementation can remain diagonal. The manager should
still be designed so a full matrix form can be added later:

```text
P = M Q + S
```

## First Definition of Done

The first complete milestone is:

```text
1. XML accepts _Netlist.
2. _Netlist is instantiated as a Type 2 boundary condition.
3. Single-tube _Netlist case runs.
4. With Rtilde=Rc and S=0, _Netlist reproduces _Resistance.
```

Only after this should the C++ netlist wrapper become part of the run path.
