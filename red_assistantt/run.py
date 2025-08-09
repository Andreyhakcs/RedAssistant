# Launcher to run as a module
import os, sys, runpy
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
runpy.run_module("red2.app", run_name="__main__")
