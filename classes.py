import os, sys, re, itertools
from shutil import copyfile


class HspiceWriter():
    """Append simulation parameters into HSPICE script file"""
    def __init__(self, filename, params):
        self.__nodes = []
        self.__filename = filename
        self.__rx_pin = ""
        self.__tx_pin = ""
        self.__params = params.copy() # Avoid side effects while being mutable for methods
        self.__stimuli = { 
            "vin1": "_i", 
            "stimuli_param": "", 
            "ven1": "_en", 
            "ven2": "_en" 
        } # may need to pass this as arg
    
    def write_params(self, line):
        # Appends Ibis model parameters to script
        if self.__params:
            for key, value in self.__params.items():
                match = re.search(r"(<" + key + r">)", line).group(1)
                if match:
                    line = line.replace(match, value)
                    del self.__params[key] # Reduce search time in subsequent iterations
                    break

    def write_netlist(self, netlist, f_obj):
        # Writes ports extracted from tstonefile and sets nodes, rx_pin, and tx_pin of instance
        f_obj.write("\n")
        for port in netlist.ports:
            for signal in netlist.signals:
                comp_pin = "gnd"
                if re.search(signal.upper(), self.__filename): 
                    comp_pin = re.search(signal.upper() + r"_(\w+\d+_\w?\d+)$", port).group(1) # need to match the comp_names
                    if not re.search(comp_pin, netlist.driver) or not re.search(comp_pin, netlist.receiver):
                        self.__nodes.append(comp_pin)
                    elif re.search(comp_pin, netlist.receiver):
                        self.__rx_pin = comp_pin
                    elif re.search(comp_pin, netlist.driver):
                        self.__tx_pin = comp_pin
                f_obj.write(f"+ {comp_pin}\t\t\t* " + port)

    def write_nodes(self, line):
        targets = ["<node_name>", "<node_name_1>", "<node_name_2>"] # need to replace res_value
        substitutes = [ re.search(r"(\w+\d+)_", self.__nodes[0]).group(1) ]
        substitutes.extend(self.__nodes)
        for i in range(len(targets)):
            line = line.replace(targets[i], substitutes[i])
    
    def write_sim_type(self, line, types):
        # Appends simulation type (ff, ss, or typ) depending on filename
        for sim_type in types:
            if re.search(sim_type, self.__filename):
                line = line.replace("<typ>", sim_type)

    # >> For future implementations:
    # def write_frequency(self, line, frequency):
    #     line = line.replace("<freq>", frequency)
    
    def write_stimuli(self, line, netlist):
        # Appends stimuli parameter depending on whether signal is a clock or data
        stimuli = self.__stimuli.copy()
        stimuli["stimuli_param"] = "pulse(0 1 0 trf trf width clk)" if re.search("clk", self.__filename) \
                else "lfsr(0 1 trf+clk/4 trf trf tdrate 1 [7,6,5,4])"
        if stimuli:
           for key, value in stimuli.items():
                match = re.search(r"(<" + key + r">)", line).group(1)
                if match:
                    comp = self.__tx_pin if key == "vi1" else self.__rx_pin
                    line = line.replace(match, comp + value)
                    del stimuli[key]
    
    def write_probes(self, line, comp_type):
        assert comp_type in ["RX", "TX"], "comp_type not 'RX' or 'TX'"
        targets = { 
            f"<{comp_type}_pin_i>" : "_i", 
            f"<{comp_type}_pin_o>" : "_o", 
            f"<{comp_type}_pin>" : "" 
        }
        for key, value in targets.items():
            comp_pin = self.__tx_pin if comp_type == "TX" else self.__rx_pin
            line = line.replace(targets[key], comp_pin + value)
    
    def make_script(self, netlist):
        # Calls instance methods to change lines in file
        with open(self.__filename, "a") as f: # Open in append mode to avoid rewrite of 
            lines = f.readlines()
            for line in lines: 
                self.write_params(line) 
                if re.search(r"typ", line):
                    self.write_sim_type(line, type(netlist).comp_types)
                elif re.search(r"s\d_trace", line):
                    self.write_netlist(netlist, f)
                elif re.search(r"\<node_name\>", line):
                    self.write_nodes(line)
                # >> For future implementations:
                # elif re.search(r"\<freq\>", line):
                #     writer.write_frequency(line, frequency)
                elif re.search(r"^v", line):
                    self.write_stimuli(line, netlist)
                elif re.search(r"^\+ v\(\<TX\)", line):
                    self.write_probes(line, "TX")
                elif re.search(r"^\+ v\(\<RX\)", line):
                    self.write_probes(line, "RX")
            f.writelines(lines)
            # >> For testing
            # return lines


class IbisBuilder():
    """Extracts parameters by crawling input directory"""
    def __init__(self, dir_path):
        os.chdir(dir_path)
        self.__dir = dir_path
        self.__name = os.path.split(dir_path)[1]
        self.__subdirs = os.listdir(dir_path) #not necessary for every proj
        print("Fetching interface parameters for project {}".format(os.path.split(os.path.abspath(".."))[1]))

    @property
    def name(self):
        return self.__name

    @property
    def tstones(self):
        # Returns dict for s-parameter file and number of ports for each net
        tstone_dict = {}
        for subdir in self.__subdirs:
            os.chdir(os.path.join(self.__dir, subdir))
            if "S-Parameter" in os.listdir("."):
                for file in os.listdir("S-Parameter"):
                    match = re.search(r"\.s(\d+)p$", file)
                    if match:
                        tstone_dict[subdir] = (file, int(match.group(1)))
                        print("Found the tstonefile {0} for interface {1}".format(file, self.__name))
            else:
                print("ERROR: Could not find 'S-Parameter folder for subdir {}".format(subdir))
                sys.exit(1)
        return tstone_dict   

    @property
    def files(self):
        # Populates file_dict with subdir name as key and each value another dict with item:file as k:v pair
        file_dict = {}
        for subdir in self.__subdirs:
            os.chdir(os.path.join(self.__dir, subdir))
            for item in os.listdir("."):
                if os.path.isdir(item):
                    os.chdir(os.path.abspath(item))
                    count = 0
                    for file in os.listdir("."): 
                        if re.search(r"(?:ibs|pkg)$", file):
                            file_dict[(subdir, item, count)] = file
                            count += 1
                    os.chdir("..")
        return file_dict

    def yield_params(self):
        # Provides dict to use for template string replacement
        for subdir in self.__subdirs:
            params = {
                "if_name": self.__name,
                "net_name": subdir,
                "tstonefile": "",
                "num_of_ports": 0,
                "TX": "",
                "TX_ibs": "",
                "TX_pkg": "",
                "RX": "",
                "RX_ibs": "",
                "RX_pkg": "",
            }

            for file_key in self.files.keys():
                if subdir == file_key[0]:
                    comp_type = "RX" if params["TX"] else "TX"
                    params[comp_type] = file_key[1]
                    file = self.files[file_key]
                    if re.search(r"(?:ibs)$", file):
                        params[f"{comp_type}_ibs"] = file # change to list if needed
                    elif re.search(r"(?:pkg)$", file):
                        params[f"{comp_type}_pkg"] = file # change to list if needed
            for tstone_key in self.tstones:
                if subdir == tstone_key:
                    params["tstonefile"] = self.tstones[tstone_key][0]
                    params["num_of_ports"] = self.tstones[tstone_key][1]
            yield params


class Netlist():
    """Extracts netlist parameters from tstonefile"""
    comp_types = ["TX", "RX"]
    sim_types = ["typ", "ff", "ss"]

    def __init__(self, params, root):
        self.__dir = os.path.join(root, params["net_name"])
        self.__params = params
        self.__ports = self.__set_ports()
        self.__signals = self.__set_signals()
        self.driver = params["TX"]
        self.receiver = params["RX"]
    
    @property
    def ports(self):
        return self.__ports
    
    @property
    def net_name(self):
        return self.__params["net_name"]

    def __set_ports(self):
        os.chdir(os.path.join(self.__dir, "S-Parameter"))
        with open(self.__params["tstonefile"]) as tsfile:
            return [ line for line in itertools.islice(tsfile, 3, 3 + (self.__params["num_of_ports"])) ]

    @property
    def signals(self):
        return self.__signals
    
    def __set_signals(self):
        if os.path.split(os.getcwd())[1] == "S-Parameter":
            os.chdir("..") # make method for dir change
        signals = []    
        for comp_type in self.comp_types:
            if not os.path.exists(comp_type):
                print(f"Generating {comp_type} folder in {os.getcwd()} for HSPICE scripts.")
                os.mkdir(comp_type)
            for port in self.ports:
                # comp_name = self.__params[comp_type]
                match = re.search(r"_(" + comp_type + r"\w{2,3})_", port)
                if match: 
                    signals.append(match.group(1)) 
        return set(signals) # need for typ ff ss

    def swap_TX_RX(self):
        self.driver, self.receiver = self.receiver, self.driver