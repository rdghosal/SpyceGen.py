import pytest, os, re
from classes import HspiceWriter, IbisBuilder, Netlist
from helpers import get_user_conf, clone_template, stringify_params

""" 
The following tests follow the four-phase
(1) setup, (2) execute, (3) verify, (4) teardown 
approach described by Gerard Meszaros 
in "xUnit Test Patterns: Refactoring Test Code" (2007).
"""

# ===================
# classes.IbisBuilder 
# ===================

def test_ibisBuilder_name():
    # Setup
    t_ibisBuilder = IbisBuilder("E:/uti/sim/Simulation/RGMII")
    
    # Execute
    name = t_ibisBuilder.name

    # Verify 
    assert name == "RGMII"

    # TearDown

def test_ibisBuilder_tstones():
    # Setup
    t_ibisBuilder = IbisBuilder("E:/uti/sim/Simulation/RGMII")

    # Execute
    tstones = t_ibisBuilder.tstones
    
    # Verify
    assert type(tstones) == dict
    assert len(tstones.keys()) == 1

    #TearDown

def test_ibisBuilder_files():
    # Setup
    t_ibisBuilder = IbisBuilder("E:/uti/sim/Simulation/RGMII")

    # Execute
    files = t_ibisBuilder.files

    # Verify
    assert type(files) == dict
    assert len(files.keys()) == 3

    # TearDown


def test_ibisBuilder_yieldParams():
    # Setup
    t_ibisBuilder = IbisBuilder("E:/uti/sim/Simulation/RGMII")

    # Execute
    params = list(t_ibisBuilder.yield_params())

    # Verify
    assert params[0]["num_of_ports"] == 17

    #TearDown