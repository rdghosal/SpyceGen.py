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
    
    def write_params(self, line):
        # Appends Ibis model parameters to the IBIS Model section of the HSPICE script
        if self.__params:
            for key, value in self.__params.items():
                match = re.search(r"(<" + key + r">)", line)
                if match:
                    line = line.replace(match.group(1), value)
                    del self.__params[key] # Reduce search time in subsequent iterations
                    break
        return line

    def write_port(self, netlist):
        # Writes ports extracted from tstonefile to the Netlist section of the HSPICE script
        # and sets nodes, rx_pin, and tx_pin of instance
        for port in netlist.ports:
            comp_pin = ""
            for signal in netlist.signals:
                if re.search(signal.lower(), self.__filename): 
                    try:
                        comp_pin = re.search(re.escape(signal) + r"_(\w+\d+_\w?\d+)", port).group(1) 
                        end = comp_pin.find("_")
                        comp = comp_pin[:end]
                        if not re.search(comp, netlist.driver) and not re.search(comp, netlist.receiver):
                            self.__nodes.append(comp_pin)
                        elif re.search(comp, netlist.receiver):
                            self.__rx_pin = comp_pin
                        elif re.search(comp, netlist.driver):
                            self.__tx_pin = comp_pin
                    except:
                        comp_pin = "gnd"
            yield f"+ {comp_pin}\t\t\t* " + port

    def write_nodes(self, line):
        # Appends nodes to the Netlist section of the HSPICE script
        placeholders = ["<node_name>", "<node_name_1>", "<node_name_2>"] # need to replace res_value
        substitutes = [ re.search(r"(\w+\d+)_", self.__nodes[0]).group(1) ]
        substitutes.extend(self.__nodes)
        for i in range(len(placeholders)):
            line = line.replace(placeholders[i], substitutes[i])
        return line
        
    def write_sim_type(self, line, types):
        # Appends simulation type (ff, ss, or typ) depending on filename 
        # to the IBIS Model section of the HSPICE script
        for sim_type in types:
            if re.search(sim_type, self.__filename):
                return line.replace("<typ>", sim_type)
                
    def write_stimuli(self, line, netlist):
        # Appends stimuli parameters depending on whether signal is a clock or data 
        # to the Stimuli section of the HSPICE script
        stimuli_param = "pulse(0 1 0 trf trf width clk)" if re.search("clk", self.__filename) \
                else "lfsr(0 1 trf+clk/4 trf trf tdrate 1 [7,6,5,4])"
        placeholders = ["TX_pin_i", "TX_pin_en", "RX_pin_en", "stimuli_param"] # Possible placeholders in template
        for i in range(len(placeholders)):
            try:
                match = re.search(r"(<" + placeholders[i] + r">)", line).group(1)
                if match and i <= 1:
                    line = line.replace(match,\
                        placeholders[i].replace("TX_pin", self.__tx_pin))
                elif match and i == 2:
                    line = line.replace(match,\
                        placeholders[i].replace("RX_pin", self.__rx_pin))
                elif match and i == 3:
                    line = line.replace(match, stimuli_param)
            except:
                continue
        return line

    def write_probes(self, line, comp_type):
        # Appends the .probe lines 
        # to the Output section of the HSPICE script
        assert comp_type in ["RX", "TX"], "comp_type not 'RX' or 'TX'"
        placeholders = { 
            f"<{comp_type}_pin_i>" : "_i", 
            f"<{comp_type}_pin_o>" : "_o", 
            f"<{comp_type}_pin>" : "" 
        }
        for key, value in placeholders.items():
            comp_pin = self.__tx_pin if comp_type == "TX" else self.__rx_pin
            line = line.replace(key, comp_pin + value)
        return line
    
    def make_script(self, netlist):
        # Calls instance methods to alter the lines in the target HSPICE script
        with open(self.__filename, "r+", encoding="utf8", errors="ignore") as f: # Open in append mode to avoid rewrite of 
            lines = f.readlines()
            for i in range(len(lines) + self.__params["num_of_ports"]): # Range accounts for line assertion in Netlist section
                lines[i] = self.write_params(lines[i]) 
                if re.search(r"typ", lines[i]):
                    lines[i] = self.write_sim_type(lines[i], type(netlist).sim_types)
                elif re.search(r"s\d_trace", lines[i]):
                    # Inserts ports into `lines`
                    lines = lines[:i+1] + [ port for port in self.write_port(netlist) ] + lines[i+1:]
                elif re.search(r"\<node_name\>", lines[i]):
                    lines[i] = self.write_nodes(lines[i])
                elif re.search(r"^v", lines[i]):
                    lines[i] = self.write_stimuli(lines[i], netlist)
                elif re.search(r"v\(<TX", lines[i]):
                    lines[i] = self.write_probes(lines[i], "TX")
                elif re.search(r"v\(<RX", lines[i]):
                    lines[i] = self.write_probes(lines[i], "RX")
            f.seek(0) # Move pointer to the start of the file
            f.writelines(lines) # Append revised lines, putting pointer at the end of the last line
            f.truncate() # Remove rest of the file, i.e., the template text
            # >> For testing
            # return lines


class IbisBuilder():
    """Extracts parameters by crawling input directory"""
    def __init__(self, dir_path):
        os.chdir(dir_path)
        self.__dir = dir_path
        self.__name = os.path.split(dir_path)[1]
        self.__subdirs = os.listdir(dir_path) #not necessary for every proj
        self.__tstones = self.__set_tstones()
        print("Fetching interface parameters for project {}".format(os.path.split(os.path.abspath(".."))[1]))

    @property
    def name(self):
        return self.__name

    @property
    def tstones(self):
        return self.__tstones

    def __set_tstones(self):
        # Returns dict for s-parameter file and number of ports for each net
        tstone_dict = {}
        for subdir in self.__subdirs:
            os.chdir(os.path.join(self.__dir, subdir))
            if "S-Parameter" in os.listdir("."):
                for file in os.listdir("S-Parameter"):
                    match = re.search(r"\.s(\d+)p$", file)
                    if match:
                        tstone_dict[subdir] = (file, int(match.group(1)))
                        print("Found the tstonefile {0} for interface {1}".format(tstone_dict[subdir][0], self.__name))
            else:
                print("ERROR: Could not find 'S-Parameter folder for subdir {}".format(subdir))
                sys.exit(1)
        return tstone_dict   

    @property
    def files(self):
        # Populates file_dict with subdir name as key 
        # and each value another dict with item:file as k:v pair
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
<<<<<<< HEAD
                "TX_comp": "",
                "TX_ibs": "",
                "TX_package": "",
                "TX_pkg": "",
                "RX": "",
                "RX_comp": "",
                "RX_ibs": "",
                "RX_package": "",
=======
                "TX_ibs": "",
                "TX_pkg": "",
                "RX": "",
                "RX_ibs": "",
>>>>>>> 4935a5aa34de9bcc51b41c8e52d2a9cfc332c0d6
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
        self.__dir = os.path.join(root, params["if_name"], params["net_name"])
        self.__params = params.copy() # Avoid side effects when manipulated by methods
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
                match = re.search(r"_(" + comp_type + r"\w{2,3})_", port)
                if match: 
                    signals.append(match.group(1)) 
        return set(signals) # eliminate duplicates

    def swap_TX_RX(self):
        self.driver, self.receiver = self.receiver, self.driver