#!/usr/bin/env python3

import os
import subprocess

# Unsafe code examples
def unsafe_exec():
    user_input = input("Enter command: ")
    exec(user_input)  # Dangerous: arbitrary code execution

def unsafe_eval():
    expr = input("Enter expression: ")
    result = eval(expr)  # Dangerous: code injection

def unsafe_subprocess():
    cmd = input("Enter command: ")
    subprocess.call(cmd, shell=True)  # Dangerous: shell injection

def unsafe_pickle():
    import pickle
    data = b"cos\nsystem\n(S'echo hello'\ntR."  # Pickle with system call
    pickle.loads(data)  # Dangerous: arbitrary code execution

if __name__ == "__main__":
    print("This file contains unsafe patterns for testing")