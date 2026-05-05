#!/usr/bin/env python
import argparse
import gc
import logging
import os
import sys
import time
import xml.etree.ElementTree as ET


SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
if SOURCE_DIR not in sys.path:
    sys.path.insert(0, SOURCE_DIR)

logger = logging.getLogger("starfish")
logger.setLevel(logging.DEBUG)


def _configure_logging(run_dir):
    os.makedirs(run_dir, exist_ok=True)
    log_path = os.path.join(run_dir, "histor.log")
    formatter = logging.Formatter("%(message)s")

    logger.handlers[:] = []
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_path, mode="w")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return log_path


def _network_name_from_xml(xml_path):
    root_tag = ET.parse(xml_path).getroot().tag
    if root_tag.endswith(".xml"):
        root_tag = root_tag[:-4]
    return root_tag or os.path.splitext(os.path.basename(xml_path))[0]


def _resolve_path(path, base_dir):
    if path is None:
        return None
    if os.path.isabs(path):
        return os.path.abspath(path)
    return os.path.abspath(os.path.join(base_dir, path))


def _normalise_data_number(data_number):
    data_number = str(data_number)
    if data_number.isdigit() and len(data_number) <= 3:
        return data_number.zfill(3)
    return data_number


def _write_description_index(results_dir, data_number, description):
    os.makedirs(results_dir, exist_ok=True)
    description_file = os.path.join(results_dir, "simulationCaseDescriptions.txt")
    lines = []
    if os.path.exists(description_file):
        with open(description_file, "r") as handle:
            lines = handle.readlines()
    else:
        lines.append("DataNumber   Description \n")

    entry = "  {} {} \n".format(data_number.ljust(10), description)
    replaced = False
    for index, line in enumerate(lines):
        parts = line.split()
        if parts and parts[0] == data_number:
            lines[index] = entry
            replaced = True
            break

    if not replaced:
        lines.append(entry)

    with open(description_file, "w") as handle:
        handle.writelines(lines)


def run_case(input_xml, output_dir, output_prefix, data_number, description, export_ascii=False, ascii_dir=None):
    import SolverLib.class1DflowSolver as c1DFlowSolv
    import UtilityLib.moduleXML as mXML
    from UtilityLib.hdf5ToAscii import export_hdf5_to_ascii

    input_xml = os.path.abspath(input_xml)
    results_dir = os.path.abspath(output_dir)
    data_number = _normalise_data_number(data_number)

    network_name = _network_name_from_xml(input_xml)
    if output_prefix is None:
        output_prefix = "{}_SolutionData_{}".format(network_name, data_number)

    solution_dir = os.path.join(results_dir, "SolutionData_{}".format(data_number))
    os.makedirs(solution_dir, exist_ok=True)

    output_hdf5 = os.path.join(solution_dir, "{}.hdf5".format(output_prefix))
    output_xml = os.path.join(solution_dir, "{}.xml".format(output_prefix))
    _write_description_index(results_dir, data_number, description)

    logger.info("____________Simulation_______________")
    logger.info("%-20s %s" % ("Input XML", input_xml))
    logger.info("%-20s %s" % ("Results dir", results_dir))
    logger.info("%-20s %s" % ("Solution dir", solution_dir))
    logger.info("%-20s %s" % ("Output HDF5", output_hdf5))
    logger.info("%-20s %s" % ("Output XML", output_xml))
    logger.info("%-20s %s" % ("Network name", network_name))
    logger.info("%-20s %s" % ("Data number", data_number))
    logger.info("%-20s %s" % ("Case description", description))

    vascular_network = mXML.loadNetworkFromXML(
        network_name,
        dataNumber=data_number,
        networkXmlFile=input_xml,
        pathSolutionDataFilename=output_hdf5,
    )
    if vascular_network is None:
        raise RuntimeError("Unable to load network XML: {}".format(input_xml))

    vascular_network.update({
        "description": description,
        "dataNumber": data_number,
        "name": network_name,
        "pathSolutionDataFilename": output_hdf5,
    })

    time_solver_init_start = time.perf_counter()
    flow_solver = c1DFlowSolv.FlowSolver(vascular_network)
    time_solver_init = time.perf_counter() - time_solver_init_start

    time_solver_solve_start = time.perf_counter()
    flow_solver.solve()
    time_solver_solve = time.perf_counter() - time_solver_solve_start

    vascular_network.saveSolutionData()
    mXML.writeNetworkToXML(vascular_network, dataNumber=data_number, networkXmlFile=output_xml)

    ascii_output_dir = None
    if export_ascii:
        ascii_output_dir = ascii_dir or os.path.join(solution_dir, "ascii")
        exported_files = export_hdf5_to_ascii(output_hdf5, output_dir=ascii_output_dir, quiet=True)
        logger.info("%-20s %s" % ("ASCII dir", ascii_output_dir))
        logger.info("%-20s %s" % ("ASCII files", len(exported_files)))

    del flow_solver
    gc.collect()

    logger.info("____________ Solver time _____________")
    logger.info("Initialisation: {:.3f} sec".format(time_solver_init))
    logger.info("Solving:        {:.3f} sec".format(time_solver_solve))
    logger.info("=====================================")

    return output_hdf5, output_xml, ascii_output_dir


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Run STARFiSh from an external case directory. "
            "By default this reads ./input.xml and writes results/SolutionData_<n>/."
        )
    )
    parser.add_argument(
        "input_xml",
        nargs="?",
        default="input.xml",
        help="Input network XML file. Default: input.xml in the current directory.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default="results",
        help="Directory for result folders. Default: ./results.",
    )
    parser.add_argument(
        "--output-prefix",
        default=None,
        help="Output filename prefix. Default: <network>_SolutionData_<data-number>.",
    )
    parser.add_argument(
        "-n",
        "--data-number",
        default="001",
        help="STARFiSh data number stored in output XML metadata. Default: 001.",
    )
    parser.add_argument(
        "-d",
        "--description",
        default="crimson_1d run",
        help="Simulation description stored in output metadata.",
    )
    parser.add_argument(
        "--export-ascii",
        action="store_true",
        help="After the run, export every HDF5 dataset to CSV files.",
    )
    parser.add_argument(
        "--ascii-dir",
        default=None,
        help="ASCII export directory. Default: <solution-dir>/ascii when --export-ascii is used.",
    )

    args = parser.parse_args(argv)
    cwd = os.getcwd()
    log_path = _configure_logging(cwd)
    input_xml = _resolve_path(args.input_xml, cwd)
    output_dir = _resolve_path(args.output_dir, cwd)
    ascii_dir = _resolve_path(args.ascii_dir, cwd)

    if not os.path.isfile(input_xml):
        if args.input_xml == "input.xml":
            parser.error(
                "required case input file './input.xml' was not found. "
                "Place the network XML at this exact name in the run directory."
            )
        parser.error("input XML file was not found: {}".format(input_xml))

    output_hdf5, output_xml, ascii_output_dir = run_case(
        input_xml=input_xml,
        output_dir=output_dir,
        output_prefix=args.output_prefix,
        data_number=args.data_number,
        description=args.description,
        export_ascii=args.export_ascii,
        ascii_dir=ascii_dir,
    )

    print("Simulation complete")
    print("  HDF5: {}".format(output_hdf5))
    print("  XML:  {}".format(output_xml))
    if ascii_output_dir is not None:
        print("  CSV:  {}".format(ascii_output_dir))
    print("  Log:  {}".format(log_path))


if __name__ == "__main__":
    main()
