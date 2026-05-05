# STARFiSh Working Reference

This is a practical map of the current STARFiSh repository for running and modifying
1D blood-flow simulations. It is written for the code in this directory, not for the
older NTNU website documentation.

## What This Code Is

STARFiSh is a Python 1D haemodynamics solver. A vascular network is described in XML:
vessels define topology, geometry, wall law, and fluid properties; boundary-condition
tags define inflow, terminal resistance, Windkessel models, etc. The solver then builds
finite-difference grids on each vessel and advances pressure, flow, and area with a
MacCormack predictor-corrector scheme.

Compared with Nektar1D, this repository is simpler in numerical machinery and input
format. Nektar1D uses a compiled code path and a structured text input file with
sections for parameters, mesh, boundary conditions, initial conditions, and history
points. STARFiSh is XML/Python driven and the network object is easier to inspect and
modify from Python, which makes it a more approachable place to prototype smarter 0D
boundary conditions.

## Important Directories

- `starfish.py`: interactive top-level menu.
- `Simulator.py`: command-line simulation entry point.
- `TemplateNetworks/`: XML template networks and inflow CSV files.
- `NetworkLib/`: vascular network, vessel, wall-law, grid, and boundary-condition data
  objects.
- `SolverLib/`: MacCormack field solver, characteristic boundary handling, junctions,
  and solver loop.
- `UtilityLib/moduleXML.py`: XML load/write path.
- `UtilityLib/networkXml043.py`: XML schema/tag map. Boundary-condition XML tags are
  mapped to Python classes here.
- `UnitTesting/`: old single-vessel regression data. The test harness expects a
  missing `UnitTesting/singleVessel/singleVessel.xml`, so use the direct single-vessel
  run below until that fixture is restored.

## Environment

Use the existing conda environment:

```bash
conda activate starfish-py3
python --version
python systemCheck.py
```

On this machine, `starfish-py3` is Python 3.11. The solver dependencies are mostly
present. `matplotlib` is not installed in that env, but the headless solver does not
need it.

Set a STARFiSh working directory once:

```bash
python Simulator.py -w /tmp/starfish_working_directory -v 0
```

STARFiSh stores copied networks and simulation output under that working directory.
The config file is `STARFiSh.config` in the repository root.

## Running Simulations

The interactive entry point is:

```bash
python starfish.py
```

For reproducible runs, use `Simulator.py` directly:

```bash
python Simulator.py -f singleVessel_template -n 012 -d single_vessel_test -v 0
```

Current command-line options used by `Simulator.py`:

- `-h`: show help.
- `-f <networkName>`: network name without `.xml`. Template names ending in
  `_template` are copied from `TemplateNetworks/` into the configured working
  directory before running.
- `-n <dataNumber>`: solution data number. Values are zero-padded to three characters,
  for example `12` becomes `012`. Existing output with the same number can be
  overwritten.
- `-d <description>`: simulation-case description. The current parser help says spaces
  are not supported, so use a compact string or quote carefully.
- `-v <mode>`: intended post-run visualisation mode: `0` none, `1` 2D and 3D, `2`
  2D, `3` 3D. Headless `-v 0` is the reliable path in this environment.
- `-r`: re-simulate from the saved XML for the supplied `-n` data number instead of
  loading the current working network XML.
- `-w <absolutePath>`: set the STARFiSh working directory and exit.
- `-p`: open working-directory settings.

Use `-v 0` for headless command-line runs. This disables post-run 2D/3D visualisation,
but it does not remove real-time visualisation communicators already present in the XML.
If a run fails with `ModuleNotFoundError: No module named 'gtk'`, remove the
`<communicators>` block from the XML or set `network.communicators = {}` before
constructing the solver.

## Smallest Headless Test Case

The bundled single-vessel template includes a real-time visualisation communicator.
For command-line/headless testing, disable communicators so the solver does not wait on
the GTK visualisation process.

```bash
conda activate starfish-py3
python - <<'PY'
import UtilityLib.moduleXML as mXML
import SolverLib.class1DflowSolver as c1dFS

network = mXML.loadNetworkFromXML(
    "singleVessel_template",
    networkXmlFile="TemplateNetworks/singleVessel_template/singleVessel_template.xml",
    pathSolutionDataFilename="/tmp/starfish_single_vessel.hdf5",
)

network.quiet = True
network.communicators = {}
network.totalTime = 0.001
network.timeSaveBegin = 0.0

solver = c1dFS.FlowSolver(network, quiet=True)
solver.solve()
network.saveSolutionData()

print("saved:", network.pathSolutionDataFilename)
print("dt:", network.dt)
print("nTSteps:", network.nTSteps)
PY
```

Expected result: the run completes and writes `/tmp/starfish_single_vessel.hdf5`. A
short run still has hundreds of time steps because STARFiSh prepends an automatic
initialisation phase.

## Input Model

A STARFiSh XML file has these important sections:

- `simulationContext`: total time, CFL, save interval, memory limit, gravity.
- `solverCalibration`: `MacCormack_Flux` or `MacCormack_Matrix`, rigid/flexible area,
  automatic grid adaptation.
- `initialisationControls`: mean flow/pressure and Windkessel compliance estimation.
- `globalFluid`: viscosity `my`, density `rho`, profile parameter `gamma`.
- `boundaryConditions`: inflow and terminal 0D models.
- `vessels`: topology, geometry, compliance/wall law, local fluid options.

The current v0.4 XML schema is version `4.3`. A minimal file has a root tag named after
the XML file and a version attribute:

```xml
<singleVessel.xml id="xxx" version="4.3">
  ...
</singleVessel.xml>
```

Important section variables:

```text
simulationContext:
  description, totalTime, CFL, timeSaveBegin, minSaveDt, maxMemory,
  gravitationalField, gravityConstant

solverCalibration:
  solvingSchemeField, rigidAreas, simplifyEigenvalues,
  riemannInvariantUnitBase, automaticGridAdaptation

initialisationControls:
  initialsationMethod, initMeanFlow, initMeanPressure,
  estimateWindkesselCompliance, compPercentageWK3,
  compPercentageTree, compTotalSys

globalFluid:
  my, rho, gamma
```

At load time, `UtilityLib/moduleXML.py` converts the XML into a
`NetworkLib.classVascularNetwork.VascularNetwork` object:

```text
VascularNetwork
  globalFluid: {my, rho, gamma}
  boundaryConditions: {vesselId: [boundaryCondition, ...]}
  vessels: {vesselId: Vessel}
  root: inlet vessel id, computed from topology
  boundaryVessels: terminal vessel ids, computed from topology
```

Each `<vessel>` becomes a `Vessel` object with four main input blocks:

```text
attributes: Id, name
topology: leftDaughter, rightDaughter, angleYMother
geometry: geometryType, length, radiusProximal, radiusDistal, N
compliance: complianceType and its wall-law parameters
fluid: applyGlobalFluid, my, rho, gamma
```

Units in XML are converted into SI values during loading. `None` values remain Python
`None` where the model supports automatic defaults, for example `Rc=None` in a
three-element Windkessel.

Core meanings:

- `totalTime`: physical simulation duration in seconds.
- `CFL`: target Courant number used to estimate the time step and check grid spacing.
- `timeSaveBegin`, `minSaveDt`, `maxMemory`: output and memory controls.
- `gravitationalField`, `gravityConstant`: enable and configure gravity terms.
- `rigidAreas`: use constant vessel area during the run.
- `simplifyEigenvalues`: use simplified characteristic speeds.
- `riemannInvariantUnitBase`: characteristic boundary formulation basis,
  `Pressure` or `Flow`.
- `automaticGridAdaptation`: allow the solver to adjust vessel `N` before solving.
- `initialsationMethod`: `Auto`, `MeanFlow`, `MeanPressure`, or `ConstantPressure`.
- `initMeanFlow`, `initMeanPressure`: reference values for initial conditions.
- `estimateWindkesselCompliance`: redistribute compliance with `No`, `Tree`, `Wk3`,
  or `System`.
- `my`, `rho`, `gamma`: blood viscosity, density, and velocity-profile parameter.

## Network File Layout

This v0.4 code uses a configurable working directory rather than the older
`networkFiles/` convention. Network inputs and outputs are organized as:

```text
TemplateNetworks/
  <networkName>_template/
    <networkName>_template.xml
    optional inflow CSV files

<workingDirectory>/
  <networkName>/
    <networkName>.xml
    <networkName>.csv       optional vessel CSV
    <networkName>BC.csv     optional boundary-condition CSV
    SolutionData_<dataNumber>/
      <networkName>_SolutionData_<dataNumber>.xml
      <networkName>_SolutionData_<dataNumber>.hdf5
```

The CSV delimiter expected by the legacy CSV helpers is semicolon `;`. A vessel CSV
uses `<networkName>.csv`; a boundary-condition CSV uses `<networkName>BC.csv`.

The old vascular network creator (`vnc.py`) can still be useful for understanding the
data model, but it is a legacy GUI/console path. In this Python 3 environment, direct
XML editing or generating XML/CSV from scripts is usually more reliable than relying on
the VNC GTK/Graphviz workflow.

## Output Model

A simulation writes two files under the configured STARFiSh working directory:

```text
<workingDirectory>/<networkName>/SolutionData_<dataNumber>/
  <networkName>_SolutionData_<dataNumber>.xml
  <networkName>_SolutionData_<dataNumber>.hdf5
```

The XML is the network definition for that run. The HDF5 file contains the saved time
series. Its main groups are:

```text
VascularNetwork/
  attrs: dt, nTSteps, nTstepsInitPhase, simulationDescription
  simulationTime      shape: (saved_time_points,)
  arterialVolume      shape: (saved_time_points,)
  TiltAngle           shape: (saved_time_points,)

vessels/
  <vessel name> - <vesselId>/
    attrs: dz, N, length
    Psol              shape: (saved_time_points, N)  pressure [Pa]
    Qsol              shape: (saved_time_points, N)  flow [m3/s]
    Asol              shape: (saved_time_points, N)  lumen area [m2]
    PositionStart     shape: (saved_time_points, 3), when available
    RotationToGlobal  shape: (saved_time_points, 3, 3), when available
    NetGravity        shape: (saved_time_points, 1), when available
```

`saved_time_points` is controlled by `timeSaveBegin`, `minSaveDt`, `totalTime`, and the
solver time step. If an automatic initialisation phase is saved, `simulationTime` can
start before zero.

For post-processing, load the network XML, call `linkSolutionData()`, then request only
the needed vessel, time range, and variables:

```python
network = mXML.loadNetworkFromXML(networkName, dataNumber=dataNumber)
network.linkSolutionData()
network.loadSolutionDataRange(
    vesselIds=[1],
    tspan=[1.0, 2.0],
    mindt=0.01,
    values=["Pressure", "Flow", "Area"],
)

P = network.vessels[1].Psol
Q = network.vessels[1].Qsol
A = network.vessels[1].Asol
t = network.tsol
```

Derived fields such as `WaveSpeed`, `Compliance`, `MeanVelocity`, and
`linearWavesplit` are computed during loading/post-processing from the saved pressure,
flow, and area arrays rather than stored as primary output.

## Mesh Structure

The vessel mesh is not a separate file. For each vessel:

```xml
<geometry>
  <geometryType>cone</geometryType>
  <length unit="m">0.5</length>
  <radiusProximal unit="m">0.0075</radiusProximal>
  <radiusDistal unit="m">0.005</radiusDistal>
  <N>50.0</N>
</geometry>
```

`NetworkLib/moduleGrids.py` converts this to:

```text
z:  axial node coordinates, shape (N,), from 0 to length
dz: spacing between neighboring nodes, shape (N - 1,)
A0: reference area at each node, shape (N,)
```

Supported geometry functions are currently:

- `uniform`: constant radius using `radiusProximal`.
- `cone`: linear radius interpolation from `radiusProximal` to `radiusDistal`.
- `constriction`: cosine constriction using `radiusProximal` as the end radius and
  `radiusDistal` as the constricted radius.

The solver stores pressure, flow, and area on the same `N` grid nodes. `N` is an input
grid-node count, not a number of elements. With `automaticGridAdaptation=True`, the
solver can increase `N` before the run to satisfy its CFL/grid-resolution checks.

## Vessel Wall And Fluid Inputs

Each vessel has a `<compliance>` block describing how cross-sectional area changes with
pressure:

```xml
<compliance>
  <complianceType>Hayashi</complianceType>
  <constantCompliance>False</constantCompliance>
  <externalPressure unit="Pa">0.0</externalPressure>
  <Ps unit="Pa">13332.0</Ps>
  <As unit="m2">None</As>
  <betaHayashi>1.83</betaHayashi>
</compliance>
```

Common compliance inputs:

- `complianceType`: one of `Laplace`, `Laplace2`, `Exponential`, `Hayashi`,
  `HayashiEmpirical`, or `Reymond`.
- `constantCompliance`: hold compliance fixed at the reference state.
- `externalPressure`: outside pressure on the vessel wall.
- `Ps`: reference pressure.
- `As`: reference area. If `None`, STARFiSh derives it from vessel radius.

Model-specific inputs include `betaLaplace`, `wallThickness`, `youngModulus`,
`betaExponential`, `betaHayashi`, and Reymond parameters `Cs`, `PmaxC`, `Pwidth`,
`a1`, and `b1`.

Each vessel also has a `<fluid>` block:

```xml
<fluid>
  <applyGlobalFluid>True</applyGlobalFluid>
  <my unit="Pa s">1e-06</my>
  <rho unit="kg m-3">1050.0</rho>
  <gamma>2.0</gamma>
</fluid>
```

When `applyGlobalFluid` is `True`, the network-level `<globalFluid>` values are used.
When it is `False`, the vessel-level `my`, `rho`, and `gamma` values override the
global values for that vessel.

## Mesh From Real-World Data

For patient/real-world geometry, the practical workflow is:

1. Extract or define the vessel graph: one row per 1D segment.
2. For each segment compute:
   - `length`: centerline length in meters.
   - `radiusProximal`, `radiusDistal`: inlet/outlet radius in meters.
   - `leftDaughter`, `rightDaughter`: child vessel IDs, or `None`.
3. Choose an initial `N`. A reasonable starting rule is:

```text
N = max(5, ceil(length_m / dx_target_m) + 1)
```

Use a smaller `dx_target_m` for short vessels or high wave-speed regions. STARFiSh can
then adjust `N` during solver initialisation if `automaticGridAdaptation` is `True`.

A useful vessel CSV schema for an XML generator would be:

```csv
Id,name,leftDaughter,rightDaughter,length_m,radiusProximal_m,radiusDistal_m,N,complianceType,Ps_Pa,betaHayashi
1,Ascending aorta,2,3,0.05,0.014,0.012,25,Hayashi,13332,1.83
2,Left branch,None,None,0.08,0.006,0.005,30,Hayashi,13332,1.83
3,Right branch,None,None,0.07,0.006,0.005,28,Hayashi,13332,1.83
```

Then emit the same XML structure as the templates. This is simpler and safer than using
the old interactive `vnc.py`, which depends on legacy GTK/pydot GUI pieces.

## Branches And Junctions

STARFiSh does not define branches in the `boundaryConditions` section the way
Nektar1D does. In Nektar1D, domain connections are explicit boundary-condition codes:
`J` for one-to-one domain connection, `B` for splitting bifurcation, `C` for merging
bifurcation, `b` for splitting trifurcation, and `X` for a two-inlet/two-outlet
junction. STARFiSh instead infers junction type from each vessel's topology fields:

```xml
<topology>
  <leftDaughter>1</leftDaughter>
  <rightDaughter>2</rightDaughter>
  <angleYMother>0</angleYMother>
</topology>
```

The topology is limited to two daughter slots per vessel:

- `leftDaughter = None`, `rightDaughter = None`: terminal vessel.
- one daughter only: serial `Link`, i.e. mother outlet connected to daughter inlet.
- two daughters: splitting `Bifurcation`, i.e. mother outlet connected to left and
  right daughter inlets.
- one daughter referenced by two different mothers: `Anastomosis`, i.e. two inlets
  merging into one outlet.

Internally, `NetworkLib/classVascularNetwork.py` traverses the topology and creates:

```python
treeTraverseConnections = [
    [leftMother, rightMother, leftDaughter, rightDaughter],
]
```

The solver interprets each row as:

```text
[M,  None, D,  None] -> Link
[M,  None, LD, RD  ] -> Bifurcation
[LM, RM,   D,  None] -> Anastomosis
```

`SolverLib/class1DflowSolver.py` turns those rows into objects from
`SolverLib/classConnections.py`. These connection objects update junction boundary
nodes every time step, between field updates and terminal boundary updates.

The nonlinear connection model solves for the incoming/outgoing characteristic
increments at the junction. For a splitting bifurcation, it enforces:

```text
Q_mother = Q_leftDaughter + Q_rightDaughter
P_mother + 0.5*rho*(Q_mother/A_mother)^2
  = P_leftDaughter + 0.5*rho*(Q_leftDaughter/A_leftDaughter)^2
P_mother + 0.5*rho*(Q_mother/A_mother)^2
  = P_rightDaughter + 0.5*rho*(Q_rightDaughter/A_rightDaughter)^2
```

For an anastomosis, the flow equation becomes:

```text
Q_leftMother + Q_rightMother = Q_daughter
```

with the same total-pressure continuity idea between each mother and the daughter.

Important limitation: there is no direct STARFiSh equivalent of Nektar1D's splitting
trifurcation `b` or two-in/two-out `X` junction. A practical workaround for a
trifurcation is to represent it as two short consecutive bifurcations, with a very short
intermediate vessel. That is a modeling approximation and should be checked for
artificial reflections. A cleaner long-term implementation would add a new connection
class and extend `evaluateConnections()` and `initializeConnections()`.

## Boundary Conditions

Boundary-condition tags are defined in `UtilityLib/networkXml043.py` and implemented in
`NetworkLib/classBoundaryConditions.py`.

In XML, boundary conditions are grouped by vessel id:

```xml
<boundaryConditions>
  <boundaryCondition vesselId="1">
    <Flow-FromFile>
      <filePathName>inflow.csv</filePathName>
      <prescribe>influx</prescribe>
      ...
    </Flow-FromFile>
  </boundaryCondition>
  <boundaryCondition vesselId="12">
    <Windkessel-3Elements>
      <Rc unit="Pa s m-3">None</Rc>
      <Rtotal unit="Pa s m-3">1.33e8</Rtotal>
      <C unit="m3 Pa-1">3.5e-8</C>
      <Z unit="Pa s m-3">VesselImpedance</Z>
    </Windkessel-3Elements>
  </boundaryCondition>
</boundaryConditions>
```

The loader creates `vascularNetwork.boundaryConditions` as:

```text
{
  vesselId: [BoundaryConditionInstance, ...]
}
```

During `VascularNetwork.initialize()`, STARFiSh assigns positions from the network
topology:

- Boundary conditions on the root vessel are placed at the inlet node `0`.
- Boundary conditions on terminal vessels are placed at the outlet node `-1`.
- For a single-vessel network only, a leading underscore in the tag name, such as
  `_Windkessel-3Elements`, marks the distal/outlet boundary on the same vessel.

The solver then splits conditions into two functional groups:

- Type 1 conditions prescribe a waveform or state increment, usually inlet flow,
  pressure, or velocity. Examples: `Flow-Sinus2`, `Flow-FromFile`,
  `Pressure-Sinus2`.
- Type 2 conditions describe the load seen through the outgoing characteristic,
  usually a terminal resistance, reflection coefficient, Windkessel, or lumped
  network. Examples: `Resistance`, `Windkessel-2Elements`,
  `Windkessel-3Elements`, `ReflectionCoefficient`.

Common type-1 prescribed waveform conditions:

- `Flow-Sinus2`: analytic sinusoidal inflow.
- `Flow-FromFile`: reads `t;Q` from a semicolon-delimited CSV. Units are seconds and
  m3/s.
- `Pressure-Sinus2`: analytic pressure boundary.

Common type-2 terminal/load conditions:

- `Resistance`: single resistance.
- `Windkessel-2Elements`: resistance plus compliance.
- `Windkessel-3Elements`: characteristic/proximal impedance plus distal resistance and
  compliance.
- `ReflectionCoefficient`: simple wave-reflection boundary.

For a single vessel, STARFiSh uses a leading underscore in the XML tag to mark a distal
boundary condition on that same vessel:

```xml
<boundaryCondition vesselId="1">
  <Flow-Sinus2>
    ...
    <prescribe>influx</prescribe>
  </Flow-Sinus2>
  <_Windkessel-3Elements>
    <Rc unit="Pa s m-3">None</Rc>
    <Rtotal unit="Pa s m-3">133000000.0</Rtotal>
    <C unit="m3 Pa-1">3.5e-08</C>
    <Z unit="Pa s m-3">VesselImpedance</Z>
  </_Windkessel-3Elements>
</boundaryCondition>
```

For multi-vessel trees, root-vessel boundary conditions are assigned to the inlet and
terminal-vessel boundary conditions are assigned to the distal end automatically.

Windkessel parameter meaning:

- `Z`: proximal/characteristic impedance. `VesselImpedance` asks STARFiSh to compute it
  from the terminal vessel.
- `Rc`: distal resistance. If `None` in the three-element model, STARFiSh uses
  `Rtotal - Z`.
- `Rtotal`: total terminal resistance.
- `C`: terminal compliance.

Compliance can also be redistributed automatically across Windkessel outlets through
`estimateWindkesselCompliance` in `initialisationControls`: `No`, `Tree`, `Wk3`, or
`System`.

## Where A Smart Boundary Manager Would Fit

The cleanest integration point is after XML loading and before `FlowSolver` creation:

```python
network = mXML.loadNetworkFromXML(...)
smart_manager.update_network_boundary_conditions(network)
solver = c1dFS.FlowSolver(network)
```

That lets the manager inspect vessel geometry, terminal IDs, resistance/compliance
targets, and measured data before the solver turns XML boundary data into numerical
`Boundary` objects. If the smart BC needs state during time stepping, the next target is
`NetworkLib/classBoundaryConditions.py`: add or modify a boundary-condition class and
register its XML tag in `UtilityLib/networkXml043.py`.

## External Case Directory Runner

The preferred workflow for `crimson_1d` is to keep source code and simulation cases
separate. A case directory should contain the network XML and any auxiliary input files
such as inflow CSV files. Outputs are written under a `results/` directory inside the
case directory.

Minimal layout:

```text
my_case/
  input.xml
  inflow.csv        # optional, only if the XML references it
```

Run from the case directory:

```bash
cd my_case
conda activate starfish-py3
python /path/to/starfish/solver.py input.xml
```

By default this writes:

```text
my_case/
  results/
    simulationCaseDescriptions.txt
    SolutionData_001/
      <networkName>_SolutionData_001.hdf5
      <networkName>_SolutionData_001.xml
```

You can choose output names:

```bash
python /path/to/starfish/solver.py input.xml --output-prefix run_001 -d "first test"
```

which writes:

```text
my_case/
  results/
    simulationCaseDescriptions.txt
    SolutionData_001/
      run_001.hdf5
      run_001.xml
```

Use `-n` to select the STARFiSh-style solution number:

```bash
python /path/to/starfish/solver.py input.xml -n 012 -d "mesh sensitivity"
```

which writes into `results/SolutionData_012/` and records the description in
`results/simulationCaseDescriptions.txt`.

Relative files referenced by `Flow-FromFile` are resolved relative to the input XML
directory, so a case can be moved as one folder without editing source-code paths.
