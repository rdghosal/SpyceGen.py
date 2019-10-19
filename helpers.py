import sys, os
from shutil import copyfile
from time import sleep


def stringify_params(params):
    # for params in params_list: #index over to allow logging 
    params_str = """
    Subdirectory/Net name: {0}
    Driver name: {1}
    Driver ibs file: {2}
    Driver package: {3}
    Receiver name: {4}
    Receiver ibs file: {5}
    Receiver package: {6}
    """.format(params["net_name"], params["driver"], 
    params["driver_ibs"], params["driver_pkg"], params["receiver"], params["receiver_ibs"], params["receiver_pkg"])

    return params_str

def clone_template(netlist, template_path):
    for signal in netlist.signals:
        for sim_type in type(netlist).sim_types:
            for comp_type in type(netlist).comp_types:
                target_filename =  "{0}_{1}_{2}_.sp".format(netlist.if_name, signal, sim_type).lower() 
                target_dir = os.path.join(os.getcwd(), comp_type, target_filename)

                copyfile(template_path, target_dir)
                print("Generating file {0} in {1}".format(target_filename, target_dir))

def get_user_conf(obj_name, param):
    print(f"Using the following parameters for {obj_name}:\n{param}")
    user_conf = ""
    while user_conf not in ["y", "n"]:
        sleep(1)
        user_conf = input("Are the above parameters correct? (y/n)")
    if user_conf is "n":
        print(f"An error occured. Please check {obj_name} and run this program again.")
        return False
    else:
        return True