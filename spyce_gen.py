#!/bin/env python3

import os, re, sys, argparse
from shutil import copyfile
from time import sleep

from helpers import stringify_params, clone_template, get_user_conf
from classes import HspiceWriter, Netlist, IbisBuilder


def main():
    
    description = """
                    This program crawls through a Simulation directory to extract
                    paramaters used to substitute placeholders in a template and generate HSPICE scripts
                    for each net in each interface.
                  """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("-p", "--path", nargs="?", required=True, help="Path to the simulation folder")
    parser.add_argument("-t", "--template", required=True, help="Path to template file")

    args = parser.parse_args()

    if os.path.split(args.path)[1] != "Simulation":
        print("ERROR: Path to 'Simulation' not provided.\nUSAGE: spyce_gen.py <directory_path>")
        sys.exit(1)

    for if_dir in os.listdir(args.path):
        i_builder = IbisBuilder(os.path.abspath(if_dir))

        for params in i_builder.yield_params():
            params_str = stringify_params(params) # params into sep class
            print(f"Using the following parameters for interface {i_builder.name} to generate HSPICE script:\n{params_str}")
            
            if not get_user_conf(i_builder.name, params_str):
                sys.exit(1)

            netlist = Netlist(params, args.path)
            conf_items ={
                "driver": netlist.driver,
                "receiver": netlist.receiver
            }
            if not get_user_conf(netlist.net_name, conf_items):
                netlist.swap_TX_RX()

            clone_template(netlist, args.template)

            for comp_type in type(netlist).comp_types:
                os.chdir(comp_type)
                sp_files = os.listdir(".")

                for file in sp_files:
                    with open(file, "a") as f:
                        lines = f.readlines()
                        writer = HspiceWriter(filename=file, file_obj=f, params=params)

                        for line in lines: 
                            writer.write_params() 
                            if re.search(r"typ", line):
                                writer.write_sim_type(line, type(netlist).comp_types)
                            elif re.search(r"s\d_trace", line):
                                writer.write_netlist(netlist)
                            elif re.search(r"\<node_name\>", line):
                                writer.write_nodes(line)
                            # elif re.search(r"\<freq\>", line):
                            #     writer.write_frequency(line, frequency)
                            elif re.search(r"^v", line):
                                writer.write_stimuli(line, netlist)
                            elif re.search(r"^\+ v\(\<TX\)", line):
                                writer.write_probes(line, comp_type="TX")
                            elif re.search(r"^\+ v\(\<RX\)", line):
                                writer.write_probes(line, comp_type="RX")

                        f.writelines(lines)
                        print(f"{file} written in folder {comp_type} of {if_dir}")

            print(f"HSPICE files generated for net {netlist.net_name}")

        print(f"Completed generating HSPICE scripts for interface {i_builder.name}")
    
    print(f"HSPICE file generation complete.")
    input("Press any key to close the program.")
    sys.exit(0)


if __name__ == "__main__":
    main()