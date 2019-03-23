"""
### purpose
# remove multiallelic sites from VariantsToTable output
###

### usage
# python filter_VariantsToTable.py VariantsToTable_outfile.txt
###
"""

import os, sys
import pandas as pd
from os import path as op
from collections import Counter


def main(thisfile, tablefile, ret=False):
    print('starting %s for %s' % (op.basename(thisfile), tablefile))

    # load the data, create a column with CHROM-POS for locusID
    df = pd.read_csv(tablefile, sep='\t')
    df['locus'] = ["%s-%s" % (contig, pos) for (contig, pos) in zip(df['CHROM'].tolist(), df['POS'].tolist())]

    # determine which loci are multiallelic
    loccount = Counter()
    for locus in df['locus']:
        loccount[locus] += 1
    goodloci = [locus for locus in loccount if loccount[locus] == 1]

    # filter df for multiallelic (multiple lines), and for SNP
    df = df[df['locus'].isin(goodloci)].copy()
    df = df[df['TYPE'] == 'SNP'].copy()

    if ret is True:
        return df
    else:
        # save
        df.to_csv(tablefile.replace(".txt", "_biallelic_snps.txt"), index=False, sep='\t')
        print('finished filtering VariantsToTable file: %s' % tablefile)


if __name__ == '__main__':
    thisfile, tablefile = sys.argv

    main(thisfile, tablefile)
