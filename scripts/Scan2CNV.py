#!/usr/bin/env python2.7
'''
This script is a wrapper for Snakemake.  The pipeline is run through rules in the Snakefile.
'''


import sys
import math
import os
import subprocess
import shutil
import argparse
import time
import glob

def makeQsub(qsubFile, qsubText):
    '''
    Make a qsub file in the qsubDir
    '''
    with open(qsubFile, 'w') as output:
        output.write('#!/bin/bash\n\n')
        output.write(qsubText)


def runQsub(qsubFile, proj, queue):
    '''
    (str, int) -> None
    '''
    qsubHeader = qsubFile[:-3]
    user = subprocess.check_output('whoami').rstrip('\n')
    qsubCall = ['qsub', '-M', user + '@mail.nih.gov', '-m', 'beas', '-q', queue, '-o', qsubHeader + '.stdout', '-e', qsubHeader + '.stderr', '-N', 'Scan2CNV.' + proj, '-S', '/bin/sh', qsubFile]
    retcode = subprocess.call(qsubCall)





def makeConfig(outDir, gtc_file_directory, bpm, project_name, pfb, hmm, scriptDir):
    '''
    (str, str, str) -> None
    '''
    paths = os.listdir(outDir)
    if 'config.yaml' in paths:
        start = getStartTime(outDir + '/config.yaml')
    else:
        start = time.ctime()
    with open(outDir + '/config.yaml', 'w') as output:
        output.write('gtc_dir: ' + gtc_file_directory + '\n')
        output.write('output_dir: ' + outDir + '\n')
        output.write('bpm: ' + bpm + '\n')
        if pfb:
            output.write('pfb: ' + pfb + '\n')
        output.write('hmm: ' + hmm + '\n')
        output.write('project_name: ' + project_name + '\n')
        output.write('repo_scripts: ' + scriptDir + '\n')
        output.write('start_time: ' + start + '\n')


def getStartTime(configFile):
    with open(configFile) as f:
        line = f.readline()
        while not line.startswith('start_time'):
            line = f.readline()
        return line.rstrip('\n').split(': ')[1]
    return time.ctime()


def get_args():
    '''
    return the arguments from parser
    '''
    parser = argparse.ArgumentParser()
    requiredArgs = parser.add_argument_group('Required Arguments')
    requiredArgs.add_argument('-n', '--name_of_project', type=str, required=True, help='Name to give to project for some output files')
    requiredArgs.add_argument('-g', '--path_to_gtc_directory', type=str, required=True, help='Full path to directory containing gtc files.  It will do a recursive search for gtc files.')
    requiredArgs.add_argument('-d', '--directory_for_output', type=str, required=True, help='REQUIRED. Full path to the base directory for the ArrayScan2CNV pipeline output')
    requiredArgs.add_argument('-b', '--bpm_file', type=str, required=True, help='REQUIRED. Full path to Illumina .bpm manifest file.')
    parser.add_argument('-p', '--pfb_file', type=str, help='Path to PennCNV PFB file.  REQUIRED for CNV calling.  Use -m option to create.')
    parser.add_argument('-hmm', '--hmm', type=str, help='Path to PennCNV hmm file.  Should be included with PennCnv download.')
    parser.add_argument('-m', '--make_pfb', action='store_true', help='use flag to indicate to generate PFB file')
    parser.add_argument('-q', '--queue', type=str, default='all.q', help='OPTIONAL. Queue on cluster to use to submit jobs.  Defaults to all of the seq queues and all.q if not supplied.  default="all.q"')
    parser.add_argument('-u', '--unlock_snakemake', action='store_true', help='OPTIONAL. If pipeline was killed unexpectedly you may need this flag to rerun')
    args = parser.parse_args()
    return args




def main():
    scriptDir = os.path.dirname(os.path.abspath(__file__))
    args = get_args()
    outDir = args.directory_for_output
    if not args.pfb_file:
        pfb = ''
    else:
        pfb = args.pfb_file
    if not args.hmm:
        hmm = ''
    else:
        hmm = args.hmm
    if outDir[0] != '/':
        print('-d argument must be full path to working directory.  Relative paths will not work.')
        sys.exit(1)
    paths = os.listdir(outDir)
    if 'logs' not in paths:
        os.mkdir(outDir + '/logs')
    if args.make_pfb:
        shutil.copy2(scriptDir + '/Snakefile_ref_files', outDir + '/Snakefile')
    else:
        shutil.copy2(scriptDir + '/Snakefile_one_samp', outDir + '/Snakefile')
    makeConfig(args.directory_for_output, args.path_to_gtc_directory, args.bpm_file, args.name_of_project, pfb, hmm, scriptDir)
    qsubTxt = 'cd ' + outDir + '\n'
    qsubTxt += 'module load sge\n'
    qsubTxt += 'module load python3/3.5.1\n'
    qsubTxt += 'module load R/3.3.0\n'
    if 'rule.dag.svg' not in paths:
       # qsubTxt += 'snakemake --dag | dot -Tsvg > dag.svg\n'
        qsubTxt += 'snakemake --rulegraph | dot -Tsvg > rule.dag.svg\n'
    if args.unlock_snakemake:
        qsubTxt += 'snakemake --unlock\n'
    qsubTxt += 'snakemake --rerun-incomplete --cluster "qsub -q ' + args.queue + ' -pe by_node {threads} '
    qsubTxt += '-o ' + outDir + '/logs/ -e ' + outDir + '/logs/" --jobs 4000 --latency-wait 300\n'
    makeQsub(outDir + '/Scan2CNV.sh', qsubTxt)
    runQsub(outDir + '/Scan2CNV.sh', os.path.basename(outDir), args.queue)
    print('Scan2CNV Pipeline submitted.  You should receive an email when the pipeline starts and when it completes.')


if __name__ == "__main__":
    main()
