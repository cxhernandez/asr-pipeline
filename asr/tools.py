from asr.configuration import *
from dendropy import Tree
import math
import re
import subprocess
import os
from Bio import Phylo  # Note, this must be version 1.63 or newer.

from asr.asrpipelinedb_api import *

from asr.argParser import *
ap = ArgParser(sys.argv)


def run_script(path):
    exe = None
    if ap.params["usempi"]:
        exe = ap.params["mpirun_exe"] + " " + path
    else:
        exe = ap.params["run_exe"] + " " + path

    os.system(exe)


def run_subprocess(command):
    args = command.split()
    proc = subprocess.Popen(args, preexec_fn=os.setsid)
    proc.wait()
    return proc


def get_mean(values):
    """Returns the mean, or None if there are 0 values."""
    if values.__len__() == 0:
        return None
    sum = 0.0
    for v in values:
        sum += float(v)
    return sum / float(values.__len__())


def get_sd(values):
    mean = get_mean(values)
    if mean is None:
        return None
    sumofsquares = 0.0
    for v in values:
        sumofsquares += (v - mean)**2
    return math.sqrt(sumofsquares / float(values.__len__()))


def get_runid(dir, model):
    nick = get_msa_nickname(dir)
    runid = nick + "." + model
    return runid


def get_phylippath(dir):
    nick = get_msa_nickname(dir)
    return dir + "/" + ap.params["geneid"] + SEP + nick + SEP + "phylip"


def get_fastapath(dir):
    nick = get_msa_nickname(dir)
    return dir + "/" + ap.params["geneid"] + SEP + nick + SEP + "fasta"


def get_trimmed_phylippath(dir):
    nick = get_msa_nickname(dir)
    return dir + "/" + ap.params["geneid"] + SEP + nick + SEP + "trim" + SEP + "phylip"


def get_trimmed_fastapath(dir):
    nick = get_msa_nickname(dir)
    return dir + "/" + ap.params["geneid"] + SEP + nick + SEP + "trim" + SEP + "fasta"


def get_raxml_phylippath(dir):
    """The phylip path for the MSA used in RAxML"""
    nick = get_msa_nickname(dir)
    return dir + "/" + ap.params["geneid"] + SEP + nick + SEP + "raxml" + SEP + "phylip"


def get_raxml_fastapath(dir):
    """The fasta path for the MSA used in RAxML"""
    nick = get_msa_nickname(dir)
    return dir + "/" + ap.params["geneid"] + SEP + nick + SEP + "raxml" + SEP + "fasta"


def get_seed_sequence(con, msaid):
    cur = con.cursor()
    sql = "select id from Taxa where shortname in (select value from Settings where keyword='seedtaxa')"
    cur.execute(sql)
    seedtaxonid = cur.fetchone()[0]

    sql = "select alsequence from AlignedSequences where almethod=" + \
        msaid.__str__() + " and taxonid=" + seedtaxonid.__str__()
    cur.execute(sql)
    seedsequence = cur.fetchone()[0]
    return seedsequence


def get_asr_fastapath(DIR):
    return get_fastapath(DIR)


def get_asr_phylippath(DIR):
    return get_phylippath(DIR)


def get_phylipstats(path):
    """Input: a path to a phylip-formatted alignment. Returns tuple (ntaxa, nsites)"""
    fin = open(path, "r")
    header = fin.readline()
    fin.close()
    tokens = header.split()
    ntaxa = int(tokens[0])
    nsites = int(tokens[1])
    return (ntaxa, nsites)


def get_raxml_infopath(DIR, model):
    runid = get_runid(DIR, model)
    return DIR + "/RAxML_info." + runid


def get_raxml_logpath(DIR, model):
    runid = get_runid(DIR, model)
    return DIR + "/RAxML_log." + runid

#
# The path to the RAxML ML tree
#


def get_raxml_treepath(DIR, runid):
    return DIR + "/RAxML_bestTree." + runid

"""The RAxML ML tree with branch supports labeled."""


def get_raxml_supportedtreepath(DIR, runid):
    return DIR + "/RAxML_bipartitions." + runid


def get_zorro_phylippath(alname, thresh):
    return alname + "/" + alname + ".tmp.zorro." + thresh.__str__() + ".phylip"


def get_fasttree_path(ppath):
    return ppath + ".fasttree"

#
# The path to the ML tree with ALR branch support.  These ALR values are
# calculated from ALRT values, generated by PhyML
#


def get_alrt_treepath(DIR, model):
    phylippath = get_raxml_phylippath(DIR)
    return phylippath + "_phyml_tree_" + model + ".alrt.txt"


def get_alr_treepath(DIR, model):
    phylippath = get_raxml_phylippath(DIR)
    return phylippath + "_phyml_tree_" + model + ".alr.tre"


def get_tree_length(path):
    """Input: path to newick tree. Returns the sum of branches on the tree."""
    t = Tree()
    t.read_from_path(path, "newick")
    return t.length()


def get_anc_cladogram(con, msaid, phylomodelid):
    """Returns the Newick-formatted string with the cladogram of ancestral
        nodes for the given alignment method (msaid) and model (phylomodelid)"""
    cur = con.cursor()
    sql = "select newick from AncestralCladogram where unsupportedmltreeid in"
    sql += "(select id from UnsupportedMlPhylogenies where almethod=" + \
        msaid.__str__() + " and phylomodelid=" + phylomodelid.__str__() + ")"
    cur.execute(sql)
    newick = cur.fetchone()[0]
    return newick


def reroot_tree(tstr):
    """Input: a tree path to a Newick tree.  Output: a re-rooted version of the tree, based on the outgroup defined in configuration.py"""
    t = Tree()
    t.read_from_string(tstr.__str__(), "newick")
    og = ap.params["outgroup"]
    og = re.sub("\[", "", og)
    og = re.sub("\]", "", og)
    og = re.sub("\"", "", og)
    ogs = og.split(",")
    mrca = t.mrca(taxon_labels=ogs)
    t.reroot_at_edge(mrca.edge, update_splits=False)
    ret = t.as_string("newick")
    ret = re.sub("\[\&\R\] ", "", ret)
    ret = ret.strip()
    return ret


#
# depricated?
#
# def reroot_tree_at_outgroup(con, newickstring):
#     """Returns a newick-formatted string containing the re-rooted vesion of the tree.
#     If something goes wrong, a message will be written to the ErrorLog table, and this
#     method will return Non."""
#     cur = con.cursor()
#
#     ogs = get_outgroup_list(con)
#
#     t = Tree()
#     t.read_from_string(newickstring.__str__(), "newick")
#     t.update_splits(delete_outdegree_one=False)
#
#     """Root the tree, temporarily, at a terminal node."""
#     t.reroot_at_midpoint(update_splits=True, delete_outdegree_one=True)
#
#     """And now re-root at the outgroup mrca"""
#     mrca = t.mrca(taxon_labels=ogs)
#     candidate_edges = []
#     for edge in t.postorder_edge_iter():
#         if edge.tail_node == mrca or edge.head_node == mrca:
#             candidate_edges.append( edge )
#     t.reroot_at_edge(mrca.edge, update_splits=False, delete_outdegree_one=True)
#     ret = t.as_string("newick")
#     ret = re.sub("\[\&\R\] ", "", ret)
#     ret = ret.strip()
#     return ret

def reroot_newick(con, newick):
    """Provide a newick string, this method will re-root the tree
        based on the 'outgroup' setting."""
    cur = con.cursor()
    dendrotree = Tree()
    dendrotree.read_from_string(newick, "newick")
    sql = "select shortname from Taxa where id in (select taxonid from GroupsTaxa where groupid in (select id from TaxaGroups where name='outgroup'))"
    cur.execute(sql)
    rrr = cur.fetchall()
    outgroup_labels = []
    for iii in rrr:
        label = re.sub("_", " ", iii[0])
        outgroup_labels.append(label.__str__())

    mrca = dendrotree.mrca(taxon_labels=outgroup_labels)
    if mrca.edge.tail_node is not None and mrca.edge.head_node is not None:
        dendrotree.reroot_at_edge(mrca.edge, update_splits=True)
    newick = dendrotree.as_string("newick")
    return newick


def get_cladogram_path(d, model):
    tpath = d + "/asr." + model + "/tree1/tree1.txt"
    fin = open(tpath, "r")
    cline = fin.readlines()[3]
    cline = cline.strip()
    cstr = re.sub(" ", "", cline)
    cstr = re.sub(";", ";", cstr)
    cstr = reroot_tree(cstr)

    cladopath = d + "/asr." + model + "/cladogram.tre"
    fout = open(cladopath, "w")
    fout.write(cstr + "\n")
    fout.close()
    return cladopath


def get_sequence(msapath, taxa):
    """msapath must be a phylip file.  Returns the seed sequence."""
    fin = open(msapath, "r")
    for l in fin.readlines():
        if l.startswith(taxa):
            tokens = l.split()
            return tokens[1]


def get_ml_sequence_from_file(path, getindels=False):
    fin = open(path, "r")
    mlseq = ""
    for l in fin.xreadlines():
        if l.__len__() > 3:
            tokens = l.split()
            state = tokens[1]
            if state != "-":
                mlseq += state.upper()
            elif getindels:
                mlseq += "-"
    return mlseq


def get_ml_sequence(site_states_probs):
    mlseq = ""
    sites = site_states_probs.keys()
    sites.sort()
    for site in sites:
        maxp = 0.0
        maxc = ""
        for c in site_states_probs[site]:
            # print site_states_probs[site][c]
            if site_states_probs[site][c] > maxp:
                maxp = site_states_probs[site][c]
                maxc = c
        if maxc != "-":
            mlseq += maxc
    return mlseq


def get_site_ml(con, ancid, skip_indels=True):
    """Returns the hashtable; key = site, value = tuple of (mlstate, mlpp)"""
    cur = con.cursor()
    sql = "select site, state, pp from AncestralStates" + ancid.__str__()
    cur.execute(sql)
    x = cur.fetchall()
    site_tuple = {}
    site_mlpp = {}
    for ii in x:
        site = int(ii[0])
        state = ii[1]
        pp = float(ii[2])
        if state == "-":
            pp = 100.0
        if site not in site_mlpp:
            site_mlpp[site] = pp
            site_tuple[site] = (state, pp)
        if pp > site_mlpp[site]:
            site_mlpp[site] = pp
            site_tuple[site] = (state, pp)

    """Indel correction:"""
    for site in site_tuple:
        found_gap = False
        if site_tuple[site][0] == "-":
            found_gap = True
            break

        if found_gap:
            if skip_indels:
                """Remove the indel site from the dictionary"""
                del site_tuple[site]
            else:
                """Correct the probability of an indel. We don't really have probs. here, so I set it to 0.0"""
                site_tuple[site] = ("-", 0.0)
    return site_tuple


def get_pp_distro(path):
    fin = open(path, "r")
    site_state_pp = {}
    for l in fin.xreadlines():
        if l.__len__() > 2:
            tokens = l.split()
            site = int(tokens[0])
            if site not in site_state_pp:
                site_state_pp[site] = []
            for ii in range(1, tokens.__len__()):
                if ii % 2 == 1:
                    state = tokens[ii].upper()
                    # print state
                    # print tokens, ii
                    prob = float(tokens[ii + 1])
                    site_state_pp[site].append([state, prob])
    return site_state_pp


def get_site_state_pp(inpath):
    fin = open(inpath, "r")
    lines = fin.readlines()
    fin.close()

    site_states_probs = {}
    for l in lines:
        tokens = l.split()
        site = int(tokens[0])
        site_states_probs[site] = {}
        i = 1
        while i < tokens.__len__():
            s = tokens[i]
            foundgap = False
            if s == "-":
                p = 0.0
                foundgap = True
            else:
                p = float(tokens[i + 1])
            if p > 1.0:
                p = 0.0
                foundgap = True
            site_states_probs[site][s] = p
            i += 2
            if foundgap:
                i = tokens.__len__()  # stop early
    return site_states_probs


def get_model_path(model, con):
    """Returns the path to a *.dat file -- a Markovian substitutions matrix."""
    modelstr = "~/Applications/paml44/dat/lg.dat"
    mmfolder = get_setting_values(con, "mmfolder")[0]
    if model.__contains__("JTT"):
        modelstr = mmfolder + "/jones.dat"
    elif model.__contains__("WAG"):
        modelstr = mmfolder + "/wag.dat"
    elif model.__contains__("LG"):
        modelstr = mmfolder + "/lg.dat"
    return modelstr


def get_pp_distro_stats(data):
    """Input: the output from get_pp_distro.  Output: mean and s.d. PP."""
    pps = []
    for site in data:
        pps.append(data[site][1])
    sum = 0.0


def binForProb(p):
    """Returns a bin number for the given probability value."""
    return int(p / 0.05)


def probForBin(b):
    """Returns the probability value for the floor of the given bin number"""
    x = float(b * 5) / float(100)
    if x == 1.00:
        return x
    return x + 0.025


def get_boundary_sites(seq, start_motif=None, end_motif=None):
    """By default the start/end are the boundaries of the provided sequence.
    But if motifs were provided, then we'll refine these boundaries."""
    startsite = 1
    endsite = seq.__len__()

    if start_motif is not None:
        if start_motif.__len__() > 0:
            for i in range(0, seq.__len__()):
                # print "258:", i, seq[i], start_motif[0]
                if seq[i] == start_motif[0]:
                    here = ""
                    j = i
                    while here.__len__() < start_motif.__len__() and j < seq.__len__():
                        # print "262:", j, here
                        if seq[j] != "-":
                            here += seq[j]
                        j += 1

                    if here == start_motif:
                        startsite = i + 1
                        break

    if end_motif is not None:
        if end_motif.__len__() > 0:
            for i in range(i, seq.__len__()):
                if seq[i] == end_motif[0]:
                    here = ""
                    j = i
                    while here.__len__() < end_motif.__len__() and j < seq.__len__():
                        if seq[j] != "-":
                            here += seq[j]
                        j += 1
                    if here == end_motif:
                        endsite = j
                        break
    return [startsite, endsite]


def align_codon_to_aaseq(con, aaseq, codonseq):
    """Maps the codon sequence to the aligned (may contain indels) aa seq."""

    # ret is the returned aligned codon sequence.
    ret = ""

    """Quick sanity check: do we have exactly 3x more nucleotides than amino acids?"""
    aa_no_indels = re.sub("-", "", aaseq)
    nt_no_indels = re.sub("-", "", codonseq)

    """Remove stop codon in the nt sequence."""
    if nt_no_indels.endswith("TAG") or nt_no_indels.endswith("TAA") or nt_no_indels.endswith("TGA"):
        nt_no_indels = nt_no_indels[0:  nt_no_indels.__len__() - 3]

    if float(aa_no_indels.__len__()) != float(nt_no_indels.__len__()) / 3.0:
        write_error(con, "The nt and aa sequence don't match.")
        print aa_no_indels.__len__(), codonseq.__len__()
        print aa_no_indels
        print nt_no_indels
        return None

    """Map the codons onto the aa sequence."""
    ntptr = 0
    for ii in range(0, aaseq.__len__()):
        codon = None
        if aaseq[ii] == "-":
            codon = "---"
        else:
            codon = nt_no_indels[ntptr: ntptr + 3]
            ntptr += 3

        ret += codon
    return ret


def get_ml_model(con, almethod):
    cur = con.cursor()
    sql = "select mltreeid, max(pp) from TreePP where mltreeid in (select id from UnsupportedMlPhylogenies where almethod=" + almethod.__str__() + ")"
    cur.execute(sql)
    x = cur.fetchall()
    if x.__len__() == 0:
        return None
    mltreeid = x[0][0]
    maxpp = x[0][1]

    sql = "select phylomodelid from UnsupportedMlPhylogenies where id=" + mltreeid.__str__()
    cur.execute(sql)
    x = cur.fetchone()[0]
    return x


def get_ancestral_matches(con, ancid1, ancid2):
    cur = con.cursor()
    sql = "select same_ancid from AncestorsAcrossModels where ancid=" + ancid1.__str__()
    cur.execute(sql)

    msas = []
    models = []

    # key = msa, value = hash; key = model, value = ancestral ID of a match to
    # ancid1
    msa_model_match1 = {}
    for ii in cur.fetchall():
        this_ancid = ii[0]
        sql = "select almethod, phylomodel from Ancestors where id=" + this_ancid.__str__()
        cur.execute(sql)
        xx = cur.fetchone()
        almethod = xx[0]
        if almethod not in msas:
            msas.append(almethod)
        phylomodelid = xx[1]
        if phylomodelid not in models:
            models.append(phylomodelid)
        if almethod not in msa_model_match1:
            msa_model_match1[almethod] = {}
        msa_model_match1[almethod][phylomodelid] = this_ancid

    sql = "select same_ancid from AncestorsAcrossModels where ancid=" + ancid2.__str__()
    cur.execute(sql)

    # key = msa, value = hash; key = model, value = ancestral ID of a match to
    # ancid2
    msa_model_match2 = {}
    for ii in cur.fetchall():
        this_ancid = ii[0]
        sql = "select almethod, phylomodel from Ancestors where id=" + this_ancid.__str__()
        cur.execute(sql)
        xx = cur.fetchone()
        almethod = xx[0]
        if almethod not in msas:
            msas.append(almethod)
        phylomodelid = xx[1]
        if phylomodelid not in models:
            models.append(phylomodelid)
        if almethod not in msa_model_match2:
            msa_model_match2[almethod] = {}
        msa_model_match2[almethod][phylomodelid] = this_ancid

    """Now find those alignment-model combinations with a match to both anc1 and anc2"""
    sql = "Select almethod from Ancestors where id=" + ancid1.__str__()
    cur.execute(sql)
    input_almethod = cur.fetchone()[0]

    msas.pop(msas.index(input_almethod))

    matches = []
    if input_almethod in msa_model_match1 and input_almethod in msa_model_match2:
        for model in models:
            if model in msa_model_match1[input_almethod] and model in msa_model_match2[input_almethod]:
                matches.append((msa_model_match1[input_almethod][
                               model], msa_model_match2[input_almethod][model]))
    else:
        print "\n. Error 296 (view_tools.py)", input_almethod, msa_model_match1.keys(), msa_model_match2.keys()

    for msa in msas:
        if msa in msa_model_match1 and msa in msa_model_match2:
            for model in models:
                if model in msa_model_match1[msa] and model in msa_model_match2[msa]:
                    matches.append(
                        (msa_model_match1[msa][model], msa_model_match2[msa][model]))
    return matches
