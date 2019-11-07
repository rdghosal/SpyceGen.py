import sys, os
from shutil import copyfile
from time import sleep


def stringify_params(params):
    """Formats params dict into appropriate str"""
    params_str = """Subdirectory/Net name: {0}
    Driver name: {1}
    Driver ibs file: {2}
    Driver package: {3}
    Receiver name: {4}
    Receiver ibs file: {5}
    Receiver package: {6}""".\
        format(params["net_name"], params["TX"],\
        params["TX_ibs"], params["TX_pkg"],\
        params["RX"], params["RX_ibs"], params["RX_pkg"])
    return params_str


def clone_template(netlist, template_path):
    """Clones template script file according to netlist instance"""
    for signal in netlist.signals:
        for sim_type in type(netlist).sim_types:
            # Format file name according to current practices
            end = netlist.net_name.find("_")
            if_name = netlist.net_name[:end]
            target_filename =  "{0}_{1}_{2}_.sp".format(if_name, signal, sim_type).lower() 
            target_dir = ""
            for comp_type in type(netlist).comp_types:
                # To ensure the RX/TX script files end up in their correct folder
                if target_filename.find(comp_type.lower()) != -1:
                    target_dir = os.path.join(os.getcwd(), comp_type)
                    if not os.path.exists(target_dir):
                        os.mkdir(target_dir)
                        break
            copyfile(template_path, os.path.join(target_dir, target_filename))
            print("Generating file {0}\n  in {1}".format(target_filename, target_dir))
    print()


def get_user_conf(obj_name, param):
    """Requests user to confirm the accuracy of given parameters"""
    print(f"\nUsing the following parameters for {obj_name}:\n    {param}")
    user_conf = ""
    while user_conf not in ["y", "n"]:
        sleep(1)
        user_conf = input("\nAre the above parameters correct? (y/n) ")
    if user_conf is "n":
        print(f"\nAn error occured. Please check {obj_name} and run this program again.")
        return False
    else:
        return True