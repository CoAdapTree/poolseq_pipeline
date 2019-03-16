### purpose
# use the GATK to realign around indels
###

### usage
# python 05_indelRealign_crisp.py /path/to/pooldir/ sampID
###

import os, sys
from os import path as op
from coadaptree import makedir


thisfile, pooldir, samp, dupfile, ref = sys.argv


# IndelRealigner
pool = op.basename(pooldir)
parentdir = op.dirname(pooldir)
aligndir  = op.join(pooldir,'04_realign')
listfile  = op.join(aligndir,'%s_realingment_targets.list' % samp)
realbam   = op.join(aligndir,'%s_realigned_reads.bam' % samp)


text = '''#!/bin/bash
#SBATCH --time=11:59:00
#SBATCH --mem=6000M
#SBATCH --ntasks=1
#SBATCH --job-name=indelRealign_%(samp)s
#SBATCH --output=indelRealign_%(samp)s_%%j.out 
#SBATCH --mail-user=lindb@vcu.edu
#SBATCH --mail-type=FAIL

module load gatk/3.8
java -Djava.io.tmpdir=$SLURM_TMPDIR -Xmx8g -jar $EBROOTGATK/GenomeAnalysisTK.jar \
-T IndelRealigner -R %(ref)s -I %(dupfile)s -targetIntervals %(listfile)s -o %(realbam)s
module unload gatk

# sbatch CRISP job if all pooled bamfiles have been created
source $HOME/.bashrc
export PYTHONPATH="${PYTHONPATH}:$HOME/pipeline"
python $HOME/pipeline/start_crisp.py %(parentdir)s %(pool)s

# next step
python $HOME/pipeline/06_lofreq.py %(pooldir)s %(samp)s %(ref)s %(realbam)s
''' % locals()

# create shdir and shfile
shdir = op.join(pooldir,'shfiles/05_indelRealign_shfiles')
makedir(shdir)
file = op.join(shdir,'indelRealign_%(samp)s.sh' % locals())
with open(file,'w') as o:
    o.write("%s" % text)

os.chdir(shdir)
print('shdir = ',shdir)
os.system('sbatch %s' % file)

os.system('python $HOME/pipeline/balance_queue.py indelRealign')
os.system('python $HOME/pipeline/balance_queue.py realign')