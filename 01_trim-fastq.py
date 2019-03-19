"""
### FIX
# customize email fail notice
###

### execution
# python 01a_trim-fastq.py /path/to/pooldir /path/to/ref.fa
###
"""


import os
import sys
import time
import shutil
import subprocess
from os import path as op
from coadaptree import fs, pklload

# args
thisfile, pooldir, ref = sys.argv
parentdir = op.dirname(pooldir)
pool = op.basename(pooldir)
f2samp = pklload(op.join(parentdir, 'f2samp.pkl'))
adaptors = pklload(op.join(parentdir, 'adaptors.pkl'))
for arg, path in [('pooldir', pooldir), ('ref', ref)]:
    if not op.exists(path):
        print("The argument does not exist in the specified path:\narg = %s\npath =%s" % (arg, path))
        sys.exit(1)


# make some dirs
shdir = op.join(pooldir, 'shfiles')
shtrimDIR = op.join(shdir, '01_trimmed_shfiles')  # cmd.sh files
trimDIR = op.join(pooldir, '01_trimmed')          # outfiles
for d in [shtrimDIR, trimDIR]:
    if not op.exists(d):
        os.makedirs(d)
mfile = op.join(parentdir, 'msgs.txt')
###


def writetomfile(text):
    with open(mfile, 'a') as m:
        m.write("%s\n" % text)


# get the fastq.gz files
os.chdir(pooldir)
gzfiles = [f for f in fs(pooldir) if 'R1' in f]
lgz = len(gzfiles)
text = 'found %(lgz)s R1 fastq.gz files in %(pooldir)s' % locals()
print(text)
writetomfile(text)

# match seq pairs, alert if pair not found
seq_pairs = []
for f in gzfiles:
    read2 = f.replace("_R1", "_R2")
    if op.exists(read2):
        seq_pairs.append((op.abspath(f), op.abspath(read2)))
    else:
        text = '\nWARNING: no pair for %s\n' % f
        writetomfile(text)

print("found %s R1/R2 seq pairs" % str(len(seq_pairs)))
text = "found %s R1/R2 seq pairs\n"
writetomfile(text)

# write sh files
shfiles = []
for r1, r2 in seq_pairs:
    samp = f2samp[r1]
    r1adaptor, r2adaptor = list(adaptors[samp].values())
    r1out = op.join(trimDIR, op.basename(r1).split(".fastq")[0] + "_trimmed.fastq.gz")
    r2out = op.join(trimDIR, op.basename(r2).split(".fastq")[0] + "_trimmed.fastq.gz")
    html = r1out.replace("R1", "").replace(".fastq.gz", "_R1_R2_stats")
    json = r1out.replace("R1", "").replace(".fastq.gz", "_R1_R2")
    logfile = r1out.replace("R1", "").replace(".fastq.gz", "_R1_R2_stats.log")

    text = '''#!/bin/bash
#SBATCH --job-name=%(pool)s-%(samp)s_trim
#SBATCH --time=02:59:00
#SBATCH --mem=5000M
#SBATCH --cpus-per-task=16
#SBATCH --output=%(pool)s-%(samp)s_trim_%%j.out
#SBATCH --mail-user=lindb@vcu.edu
#SBATCH --mail-type=FAIL

source $HOME/.bashrc
export PYTHONPATH="${PYTHONPATH}:$HOME/pipeline"
module load fastp/0.19.5

fastp -i %(r1)s -o %(r1out)s -I %(r2)s -O %(r2out)s --disable_quality_filtering \
-g --cut_window_size 5 --cut_mean_quality 30 --n_base_limit 20 --length_required 75 \
-h %(html)s.html --cut_by_quality3 --thread 16 --json %(json)s.json \
--adapter_sequence %(r1adaptor)s --adapter_sequence_r2 %(r2adaptor)s > %(logfile)s

# once finished, map using bwa mem 
python $HOME/pipeline/02_bwa-map_view_sort_index_flagstat.py %(ref)s %(r1out)s %(r2out)s %(shdir)s %(samp)s

''' % locals()
    filE = op.join(shtrimDIR, '%(pool)s-%(samp)s_trim.sh' % locals())
    shfiles.append(filE)
    with open(filE, 'w') as o:
        o.write("%s" % text)

print('shcount =', len(shfiles))
print('shdir = ', shtrimDIR)
# qsub the files
print(shfiles)
for sh in shfiles:
    os.chdir(op.dirname(sh))     # want sbatch outfiles in same folder as sh file
    print('shfile=',sh)
    subprocess.call([shutil.which('sbatch'), sh])
    # os.system('sbatch %s' % sh)
    time.sleep(2)
