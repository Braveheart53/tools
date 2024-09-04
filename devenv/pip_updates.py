# -*- coding: utf-8 -*-
"""
Edited on Tue Sep  3 16:46:01 2024
@author: omasoud
@Editor: Braveheart53
Python Version Testing: his has been tested on anaconda most recent version and python 3.8 & 3.12

Purpose: 
This script is a fork of the pip_updates.py script from the listed @author. 
It finds and updates any modules that were installed via pip in a conda installation. 
It leaves all modules installed via conda alone
"""
import argparse
import traceback
import yaml
import json
import subprocess
# import concurrent.futures
# from multiprocessing import Process, Lock, Pool

def get_powershell_stdout(cmd):
    """
    Parameters
    ----------
    cmd : string
        DESCRIPTION.

    Raises
    ------
    RuntimeError
        DESCRIPTION.

    Returns
    -------
    result.stdout : dict
        DESCRIPTION.

    """
    # slowest operation in the script
    result = subprocess.run(['powershell.exe', '-NonInteractive', 
                             '-NoProfile',  '-Command', cmd], 
                            capture_output=True) # Assuming not needed: '-ExecutionPolicy', 'Unrestricted'
    if (result.stderr):
        s_err=result.stderr.decode('utf8',errors='ignore')
        raise RuntimeError(s_err)
        out = result.stdout.decode('utf8',errors='ignore')
        return out
    return result.stdout

def get_packages(env):
    """
    Parameters
    ----------
    env : STRING
        conda environment name

    Returns
    -------
    all_packages : TYPE
        DESCRIPTION.
    pip_outdated : TYPE
        DESCRIPTION.

    """
    print('Querying conda to get pip packages...')
    cmd = (rf'& "$env:LOCALAPPDATA\Anaconda3\shell\condabin\conda-hook.ps1" ' +
           '; conda activate ' + env + ' ; conda env export')
    all_packages=yaml.safe_load(get_powershell_stdout(cmd))
    print('Querying pip to get outdated packages...')
    cmd = (rf'& "$env:LOCALAPPDATA\Anaconda3\shell\condabin\conda-hook.ps1" ;' +
           ' conda activate ' + env + ' ; pip list --outdated --format=json')
    pip_outdated=json.loads(get_powershell_stdout(cmd))
    return all_packages, pip_outdated


if __name__ == '__main__':

    # condaEnvName = 'base'
    parser = argparse.ArgumentParser(
        description='Produce pip update commands '+
                                  ' for outdated ' + 
                                  'packages that are not conda packages.')
    parser.add_argument('--env',
                        action='store', metavar='CONDA_ENV', 
                     required = True,
                     help='The conda environment to be checked. '+
                     'For example, for base environment enter "--env base".')

    args = parser.parse_args()

    try:
        all_packages, pip_outdated =  get_packages(args.env)
        
        # parallelize this?
        pips=[d['pip'] for d in all_packages['dependencies']
              if isinstance(d,dict) and 'pip' in d]
        
        assert len(pips)==1
        pips=pips[0]
        pips=[d.split('==')[0] for d in pips]
        outdated=[p for p in pip_outdated]
        candidates=[p for p in outdated if p['name'] in pips]
        print(f'\nThere are a total of {len(pips)} pip (non-conda) packages.')
        print(f'pip reports there are {len(outdated)} packages that are out of date.')
        print(f'Of those, the non-conda ones are: {len(candidates)}.')
        if candidates:
            print(f'\nHere are the current and latest versions for these {len(candidates)}:')
            cols = (max([len(p['name']) for p in candidates]), 
                    max([len(p['version']) for p in candidates]), 
                    max([len(p['latest_version']) for p in candidates]))
            for p in candidates:
                print(f'{p["name"]+": ":<{cols[0]+2}}{p["version"]:<{cols[1]}} -> {p["latest_version"]:<{cols[2]}}')
            print('\nAnd here are the pip update commands for those:\n')
        else:
            print('There is nothing to update.')
        update_cmds=[f'pip install {p["name"]} --upgrade' for p in candidates]
        print('\n'.join(update_cmds))

        print()
        print('Finished.')

    except ValueError as e:
        print('\nCannot proceed due to the following:')
        print(e)

    except Exception as e:
        print('\nUnexpected error. Please report to author:')
        print(e)

        print()
        print('-----TRACEBACK------')
        print(traceback.format_exc()) # for debugging
