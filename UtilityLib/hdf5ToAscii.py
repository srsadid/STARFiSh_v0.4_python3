#!/usr/bin/env python
import argparse
import os


def _safe_dataset_filename(name):
    return name.strip("/").replace("/", "_").replace(" ", "_") or "root"


def export_hdf5_to_ascii(input_file, output_dir=None, delimiter=",", fmt="%.6e", quiet=False):
    """
    Export every dataset in a STARFiSh HDF5 solution file to simple CSV files.

    Higher-dimensional arrays are flattened to two dimensions by preserving the
    first axis and folding the remaining axes into columns.
    """
    os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")

    import h5py
    import numpy as np

    input_file = os.path.abspath(input_file)
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(input_file), "ascii")
    output_dir = os.path.abspath(output_dir)

    if not os.path.isfile(input_file):
        raise FileNotFoundError("HDF5 file was not found: {}".format(input_file))

    os.makedirs(output_dir, exist_ok=True)
    exported_files = []
    manifest_path = os.path.join(output_dir, "manifest.txt")

    with h5py.File(input_file, "r") as h5_file, open(manifest_path, "w") as manifest:
        manifest.write("source: {}\n".format(input_file))
        manifest.write("dataset,shape,dtype,file\n")

        def export_dataset(name, obj):
            if not isinstance(obj, h5py.Dataset):
                return

            filename = "{}.csv".format(_safe_dataset_filename(name))
            filepath = os.path.join(output_dir, filename)
            data = np.asarray(obj)

            if data.ndim == 0:
                with open(filepath, "w") as out_file:
                    out_file.write(str(data.item()))
                    out_file.write("\n")
            elif data.ndim <= 2:
                np.savetxt(filepath, data, delimiter=delimiter, fmt=fmt)
            else:
                np.savetxt(filepath, data.reshape(data.shape[0], -1), delimiter=delimiter, fmt=fmt)

            exported_files.append(filepath)
            manifest.write("{},{},{},{}\n".format(name, data.shape, data.dtype, filename))
            if not quiet:
                print("Exported: {}".format(name))

        h5_file.visititems(export_dataset)

    exported_files.append(manifest_path)
    return exported_files


def main(argv=None):
    parser = argparse.ArgumentParser(description="Export STARFiSh HDF5 solution datasets to CSV files.")
    parser.add_argument("input_file", help="Path to a STARFiSh .hdf5 solution file.")
    parser.add_argument(
        "-o",
        "--output-dir",
        default=None,
        help="Output directory. Default: ./ascii next to the HDF5 file.",
    )
    parser.add_argument("--delimiter", default=",", help="Output delimiter. Default: comma.")
    parser.add_argument("--fmt", default="%.6e", help="Numeric format for numpy.savetxt. Default: %%.6e.")
    args = parser.parse_args(argv)

    exported_files = export_hdf5_to_ascii(
        args.input_file,
        output_dir=args.output_dir,
        delimiter=args.delimiter,
        fmt=args.fmt,
    )
    print("Exported {} files.".format(len(exported_files)))


if __name__ == "__main__":
    main()
