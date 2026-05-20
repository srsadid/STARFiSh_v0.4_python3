class NetlistBoundaryManager(object):
    """
    Python-side coordination point for netlist boundary coupling.

    A STARFiSh case owns one global CRIMSON netlist file, conventionally named
    netlist_surfaces.xml. Individual STARFiSh boundaries register by surfaceId;
    the surfaceId maps that 1D boundary to one interface circuit/surface inside
    the shared netlist file.
    """

    def __init__(self):
        """
        Start with no registered STARFiSh boundaries and no loaded CRIMSON
        bridge. The bridge is created lazily the first time a real netlist
        coefficient is requested.
        """
        self.boundaries = {}
        self.boundary_states = {}
        self.pending_states = {}
        self.netlist_file = None
        self.adapter = None

    def register_boundary(
        self,
        surface_id,
        vessel_id=None,
        position=None,
        netlist_file=None,
        flow_sign=1.0,
        rtilde=None,
        s=0.0,
    ):
        """
        Register one STARFiSh boundary against one CRIMSON surface id.

        This is called while STARFiSh reads input.xml. Multiple calls can point
        at the same global netlist_surfaces.xml file. Each call only adds the
        local 1D metadata needed later in the timestep loop:

        surface_id -> vessel_id, boundary position, flow sign, optional fake
        coefficients.
        """
        surface_id = int(surface_id)
        if netlist_file is not None:
            self.set_netlist_file(netlist_file)
        self.boundaries[surface_id] = {
            "vessel_id": vessel_id,
            "position": position,
            "flow_sign": float(flow_sign),
            "rtilde": rtilde,
            "s": s,
        }

    def set_netlist_file(self, netlist_file):
        """
        Set the one CRIMSON netlist file for the whole STARFiSh case.

        CRIMSON's netlist file contains all outlet/interface circuits. This
        manager deliberately rejects a second different file because that would
        imply each surface has its own netlist, which is not the CRIMSON model.
        """
        if self.netlist_file is not None and self.netlist_file != netlist_file:
            raise ValueError(
                "Only one global netlist_surfaces.xml file is supported per STARFiSh run. "
                "Existing: {}; requested: {}".format(self.netlist_file, netlist_file)
            )
        self.netlist_file = netlist_file

    def compute_coefficients(self, surface_id, timestep, time, dt, pressure, flow):
        """
        Return the affine netlist law for one surface:

            P = dp_dq * Q + Hop

        During the 1D boundary update, netlistInterface asks this method for
        the current surface's `(dp_dq, Hop)`. If `Rtilde/S` were supplied in
        input.xml, this returns those constants for fake/resistance testing.
        Otherwise it forwards the request to the single CRIMSON adapter.
        """
        surface_id = int(surface_id)
        boundary = self.boundaries.get(surface_id)
        if boundary is None:
            raise KeyError("No netlist boundary registered for surfaceId {}".format(surface_id))
        if boundary["rtilde"] is not None:
            return float(boundary["rtilde"]), float(boundary["s"])
        adapter = self._get_adapter(dt)
        return adapter.compute_implicit_coefficients(surface_id, timestep, time, dt, flow)

    def record_boundary_state(self, surface_id, timestep, time, dt, pressure, flow):
        """
        Store the final 1D interface state after the characteristic solve.

        This mirrors the CRIMSON flow: each surface first computes its final
        interface pressure/flow, then the global netlist is advanced once at
        the end of the timestep. Therefore this method only records state; it
        does not immediately update/finalize CRIMSON.
        """
        surface_id = int(surface_id)
        state = {
            "timestep": timestep,
            "time": time,
            "dt": dt,
            "pressure": pressure,
            "flow": flow,
        }
        self.boundary_states[surface_id] = state
        boundary = self.boundaries.get(surface_id)
        if boundary is not None and boundary["rtilde"] is None:
            self.pending_states[surface_id] = state

    def finalize_timestep(self, timestep):
        """
        Finalize the global CRIMSON netlist once for a timestep.

        This should be called after the solver has visited all boundary objects
        for the timestep. It pushes every recorded real-netlist surface state
        into CRIMSON, then advances/finalizes the one global netlist.
        """
        if self.pending_states:
            first_state = next(iter(self.pending_states.values()))
            adapter = self._get_adapter(first_state["dt"])
            for surface_id in sorted(self.pending_states):
                state = self.pending_states[surface_id]
                adapter.update_state(
                    surface_id,
                    state["timestep"],
                    state["time"],
                    state["dt"],
                    state["pressure"],
                    state["flow"],
                )
            adapter.finalize_timestep(timestep)
            self.pending_states.clear()
        elif self.adapter is not None:
            self.adapter.finalize_timestep(timestep)
        return None

    def _get_adapter(self, dt):
        """
        Lazily construct the one Python-to-C++ adapter for this case.

        The manager keeps STARFiSh boundary bookkeeping. The adapter only owns
        the compiled CRIMSON bridge for the global netlist_surfaces.xml file.
        """
        if self.netlist_file is None:
            raise ValueError(
                "Netlist adapter mode requires netlist_surfaces.xml next to input.xml."
            )
        if self.adapter is None:
            from UtilityLib.crimsonNetlistAdapter import CrimsonNetlistAdapter
            self.adapter = CrimsonNetlistAdapter(
                self.netlist_file,
                delt=dt,
                surface_ids=sorted(self.boundaries.keys()),
            )
            self.adapter.load(dt)
        return self.adapter


_DEFAULT_MANAGER = NetlistBoundaryManager()


def get_default_netlist_manager():
    """
    Return the process-wide manager used by STARFiSh boundary condition objects.
    """
    return _DEFAULT_MANAGER
