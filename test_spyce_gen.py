import pytest, os, re
from classes import HspiceWriter, IbisBuilder, Netlist
from helpers import get_user_conf, clone_template, stringify_params

""" 
The following tests follow the four-phase
(1) setup, (2) execute, (3) verify, (4) teardown 
approach described by Gerard Meszaros 
in "xUnit Test Patterns: Refactoring Test Code" (2007).
"""
# 
#   __CLASSES__
# 
# ==========================
#   classes.IbisBuilder 
# ==========================

# Setup - global instance
t_root = r"E:/uti/sim/Simulation/RGMII"
t_ibisBuilder = IbisBuilder(t_root)

def test_ibisBuilder_name():
    
    # Execute
    name = t_ibisBuilder.name

    # Verify 
    assert name == "RGMII"

    # TearDown


def test_ibisBuilder_tstones():

    # Execute
    tstones = t_ibisBuilder.tstones
    
    # Verify
    assert type(tstones) == dict
    assert len(tstones.keys()) == 1

    #TearDown


def test_ibisBuilder_files():

    # Execute
    files = t_ibisBuilder.files

    # Verify
    assert type(files) == dict
    assert len(files.keys()) == 3

    # TearDown


def test_ibisBuilder_yieldParams():

    # Execute
    params = list(t_ibisBuilder.yield_params())

    # Verify
    assert params[0]["num_of_ports"] == 17

    #TearDown


# ==========================
#   classes.Netlist 
# ==========================

# Setup - global instance, params
t_params = {
    'if_name': 'RGMII', 
    'net_name': 'RGMII_IZ01_IB01', 
    'tstonefile': 'yyMMdd_test_tstonefile.s17p', 
    'num_of_ports': 17, 
    'TX': 'IB01', 
    'TX_ibs': 'sak-tc397xe256f300sa.ibs', 
    'TX_pkg': '', 
    'RX': 'IZ01', 
    'RX_ibs': 'e6352_e6176.ibs', 
    'RX_pkg': 'sak-tc397xe256f300sa.pkg'
    }
t_netlist = Netlist(t_params, t_root)


def test_netlist_props():
    
    # Execute 
    actual_name = t_netlist.net_name
    actual_receiver = t_netlist.receiver
    actual_driver = t_netlist.driver
    actual_signals = t_netlist.signals

    # Verify
    assert actual_name == t_params["net_name"]
    assert actual_receiver == t_params["RX"]
    assert actual_driver == t_params["TX"]
    assert len(actual_signals) == 4

    # TearDown


def test_netlist_ports():

    # Execute 
    actual = t_netlist.ports

    # Verify
    assert isinstance(actual, list)
    assert len(actual) == 17

    # TearDown


def test_netlist_swap():

    # Setup
    original_rx = t_netlist.receiver
    original_tx = t_netlist.driver

    # Execute
    t_netlist.swap_TX_RX()

    # Verify
    assert t_netlist.receiver == original_tx
    assert t_netlist.driver == original_rx

    # TearDown


# ==========================
#   classes.HspiceWriter
# ==========================

# Set up - global instance and dictionary for args in method testing

def test_make_script():
    # Setup
    t_spfile = os.path.join(os.getcwd(), "RX", "rgmii_rxclk_ff_.sp")
    print(t_spfile)
    t_hswriter = HspiceWriter(t_spfile, t_params) # `t_params` from `class.Netlist` test
    expected_lines = []

    # Execute
    actual_lines = t_hswriter.make_script(t_netlist)

    # Verify
    assert expected_lines == actual_lines




t_lines = {
    "ibis": [
        "+ file='<TX_file>'",
        "+ component='<TX_comp>'",
        "+ package='<TX_package>'",
        "+ pkgfile='<TX_pkg>'",
        "*+ mod_sel='Selection_1='",
    ], 
    "sim_type": "+ typ=typ"
}

#
#   __HELPER FUNCTIONS__
#
# ==========================
#   helpers.stringify_params
# ==========================

def test_stringify_params():

    # Setup
    # arg `params` already prepared for `classes.Netlist` test
    expected = """
    Subdirectory/Net name: RGMII_IZ01_IB01
    Driver name: IB01
    Driver ibs file: sak-tc397xe256f300sa.ibs
    Driver package: 
    Receiver name: IZ01
    Receiver ibs file: e6352_e6176.ibs
    Receiver package: sak-tc397xe256f300sa.pkg
    """

    # Execute
    actual = stringify_params(t_params)

    # Verify
    assert type(actual) == str
    assert actual == expected

    #  Teardown


def test_clone_template():

    # Setup
    # Using Netlist instance from test `classes.Netlist`
    t_temp_path = "E:\\uti\\sim\\template_test.txt"
    tx_path = os.path.join(os.getcwd(), "TX")
    rx_path = os.path.join(os.getcwd(), "RX")

    # Execute
    clone_template(t_netlist, t_temp_path)

    # Verify
    # Ensures typ, ff, ss versions have been generated for each script
    for sim_type in Netlist.sim_types:
        # Asserts files exist in directory
        assert os.listdir(rx_path).index(f"rgmii_rxclk_{sim_type}_.sp") != -1 
        assert os.listdir(tx_path).index(f"rgmii_txd2_{sim_type}_.sp") != -1 

    # Teardown