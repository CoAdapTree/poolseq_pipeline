"""
### usage
# python 00_start-pipeline.py /path/to/folder/with/all/fastq/files/
###
"""

import os, sys, distutils.spawn, pandas as pd, balance_queue, subprocess, shutil
from os import path as op
from collections import OrderedDict
from coadaptree import fs, pkldump, uni, luni


class Bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
###

# args
thisfile, parentdir = sys.argv


print(Bcolors.BOLD + Bcolors.OKGREEN + '''
******************************************************************************************************


               ___|                 \          |              _   __|
              |       _ \            \     __  |   _      _      |      _|    _ \\    _ \\
              |      (   | __|    /_  \   (    |  (   |  (  |    |     |      __/    __/
               ___| \___/       _/    _\ \___/_| \__/_|   __/    |    _|    \___|  \___|
                                                         |
                                                         |

                                      LoFreq and CRISP pipeline

******************************************************************************************************


''' + Bcolors.ENDC)

# check python version
pyversion = str(sys.version_info[0]) + '.' + str(sys.version_info[1]) + '.' + str(sys.version_info[2])
if not sys.version_info[0] == 3:
    text = '''FAIL: You are using python %s. This pipeline was built with python 3.7+.
FAIL: Please use a more recent version of python.
FAIL: exiting %s
''' % (pyversion, thisfile)
    print(Bcolors.BOLD + Bcolors.FAIL + text + Bcolors.ENDC)
    exit()
if not sys.version_info[1] == 7:
    text = "WARN: You are using python v%s. This pipeline was built with python v3.7+.\n" \
           "WARN: You may want to consider updating to a more recent version of python.\n" % pyversion
    print(Bcolors.BOLD + Bcolors.WARNING + text + Bcolors.ENDC)
    while True:
        inp = input("INPUT NEEDED: Do you want to proceed? (yes | no): ").lower()
        if inp in ['yes', 'no']:
            break
        else:
            print("Please respond with 'yes' or 'no'")
    if inp == 'no':
        print('exiting %s' % thisfile)
        exit()

# check for assumed exports
print('\nchecking for exported variables')
for var in ['SLURM_ACCOUNT', 'SBATCH_ACCOUNT', 'SALLOC_ACCOUNT',
            'CRISP_DIR', 'PYTHONPATH', 'SQUEUE_FORMAT']:
    try:
        print('\t%s = %s' % (var, os.environ[var]))
    except KeyError:
        print('\tcould not find %s in exported vars\nexiting %s' % (var, thisfile))
        exit()
for exe in ['lofreq', 'activate']:
    if distutils.spawn.find_executable(exe) is None:
        print('\tcould not find %s in $PATH\nexiting %s' % (exe, thisfile))
        if exe == 'activate':
            print('\t\t(the lack of activate means that the python env is not correctly installed)')
        exit()
print('DONE!\n')

# read in the datatable, save rginfo for later
if parentdir.endswith("/"):
    parentdir = parentdir[:-1]
datatable = op.join(parentdir, 'datatable.txt')
if not op.exists(datatable):
    print('the datatable is not in the necessary path: %s\nexiting %s' % (datatable, thisfile))
    sys.exit(3)
print('reading datatable, getting fastq info')
data = pd.read_csv(datatable, sep='\t')
rginfo = {}  # key=sampname vals=rginfo
samp2pool = {}  # key=samp val=pool
poolref = {}  # key=pool val=ref.fa
ploidy = {}  # key=pool val=ploidy
poolsamps = {}  # key=pool val=sampnames
f2samp = {}  # key=f val=samp
f2pool = {}  # key=f val=pool
adaptors = OrderedDict()  # key=samp val={'r1','r2'} val=adaptor
for row in data.index:
    samp = data.loc[row, 'sample_name']
    adaptors[samp] = {'r1': data.loc[row, 'adaptor_1'],
                      'r2': data.loc[row, 'adaptor_2']}
    pool = data.loc[row, 'pool_name']
    pooldir = op.join(parentdir, pool)
    print('{}\tsamp = {}\tpool = {}'.format(row, samp, pool))
    if pool not in poolsamps:
        poolsamps[pool] = []
    if samp not in poolsamps[pool]:
        poolsamps[pool].append(samp)
    samp2pool[samp] = pool
    df = data[data['pool_name'] == pool].copy()
    if not luni(df['ploidy']) == 1:
        print("the ploidy values for some elements with pool name '%s' are not the same" % pool)
        sys.exit(1)
    if pool not in ploidy:
        ploidy[pool] = data.loc[row, 'ploidy']
    if pool in poolref:
        if not poolref[pool] == data.loc[row, 'ref']:
            print("ref genome for samples in %s pool seems to have different paths in datatable.txt" % pool)
            sys.exit(1)
    else:
        ref = data.loc[row, 'ref']
        if not op.exists(ref):
            print('ref for %s does not exist in path: %s' % (samp, ref))
            print('exiting %s' % thisfile)
            exit()
        poolref[pool] = ref
    rginfo[samp] = {}
    for col in ['rglb', 'rgpl', 'rgsm']:  # rg info columns
        rginfo[samp][col] = data.loc[row, col]
    for f in [data.loc[row, 'file_name_r1'], data.loc[row, 'file_name_r2']]:
        f2pool[f] = pool
        f2samp[op.join(pooldir, f)] = samp
pkldump(rginfo, op.join(parentdir, 'rginfo.pkl'))
pkldump(ploidy, op.join(parentdir, 'ploidy.pkl'))
pkldump(f2samp, op.join(parentdir, 'f2samp.pkl'))
pkldump(poolsamps, op.join(parentdir, 'poolsamps.pkl'))
pkldump(poolref, op.join(parentdir, 'poolref.pkl'))
pkldump(adaptors, op.join(parentdir, 'adaptors.pkl'))


def create_crisp_bedfiles():
    import create_bedfiles  # so I don't have to worry about namespace interference
    # create bedfiles for crisp
    print("\ncreating CRISP bedfiles")
    for ref in poolref.values():
        create_bedfiles.main('create_bedfiles.py', ref)
        # os.system('python $HOME/pipeline/create_bedfiles.py %s' % ref)


create_crisp_bedfiles()


# make pool dirs
print("\nmaking pool dirs")
pools = uni(data['pool_name'].tolist())
pooldirs = []
for p in pools:
    DIR = op.join(parentdir, p)
    if not op.exists(DIR):
        os.makedirs(DIR)
    if op.exists(DIR):
        pooldirs.append(DIR)

# get list of files from datatable, make sure they exist in parentdir, create symlinks in /parentdir/<pool_name>/
print('\nchecking for existance of fastq files in datatable.txt')
files = [f for f in fs(parentdir) if 'fastq' in f and 'md5' not in f]
datafiles = data['file_name_r1'].tolist()
for x in data['file_name_r2'].tolist():
    datafiles.append(x)

for f in datafiles:
    src = op.join(parentdir, f)
    if not op.exists(src)   :
        # make sure file in datatable exists
        print("could not find %s in %s\nmake sure file_name in datatable is its basename" % (f, parentdir))
        sys.exit(1)
    pooldir = op.join(parentdir, f2pool[f])
    dst = op.join(pooldir, f)
    if not op.exists(dst):
        # easy to visualize in cmdline if script is finding correct group of files
        os.symlink(src, dst)

# create sh files
print('\nwriting sh files')
for pooldir in pooldirs:
    pool = op.basename(pooldir)
    print('\npool = %s' % pool)
    ref = poolref[pool]
    subprocess.call([shutil.which('python'), op.join(os.environ['HOME'], 'pipeline/01_trim-fastq.py'), pooldir, ref])
    # os.system('python 01_trim-fastq.py %(pooldir)s %(ref)s' % locals())
print('\n')

balance_queue.main('balance_queue.py', 'trim')
