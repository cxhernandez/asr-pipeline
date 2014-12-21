from log import *
from tools import *
from asrpipelinedb_api import *

def get_dnds_commands(con):
    """Returns the path to a script that can be launched by MPIrun"""    
    cur = con.cursor()
    
    sql = "delete from LabeledDnDsPhylogenies"
    cur.execute(sql)
    con.commit()
    sql = "delete from DNDS_Tests"
    cur.execute(sql)
    con.commit()
    sql = "delete from DNDS_Models"
    cur.execute(sql)
    con.commit()
    sql = "delete from DNDS_lnL"
    cur.execute(sql)
    con.commit()
    
    if False == os.path.exists("dnds"):
        os.system("mkdir dnds")
        
    commands = []
        
    codeml_exe = get_setting_values(con, "codeml_exe")
    if codeml_exe == None:
        write_error(con, "I cannot find the executable for codeml. Error 29")
        exit()
    else:
        codeml_exe = codeml_exe[0]
        
    """For each msa/model/anccomp pair, create a labeled ML tree with #1 label on the branch of interest."""
    for msa in get_alignment_method_names(con):
        sql = "select id from AlignmentMethods where name='" + msa + "'"
        cur.execute(sql)
        msaid = cur.fetchone()[0]

        for model in get_phylo_modelnames(con):
            sql = "select modelid from PhyloModels where name='" + model + "'"
            cur.execute(sql)
            modelid = cur.fetchone()[0]
            
            unsupported_newick = None
            sql = "select newick from UnsupportedMlPhylogenies where almethod=" + msaid.__str__() + " and phylomodelid=" + modelid.__str__()
            cur.execute(sql)
            x = cur.fetchall()
            if x.__len__() == 0:
                write_error(con, "I can't find your ML phylogeny. Error 34.")
                exit()
            unsupported_newick = x[0][0]
                        
            mltree = Tree()
            mltree.read_from_string(unsupported_newick.__str__(), "newick")
            
            for pair in get_ancestral_comparison_pairs(con):
                ancid1 = get_ancestorid(con, pair[0], msaid, modelid)
                ancid2 = get_ancestorid(con, pair[1], msaid, modelid)
  
                taxaids1 = get_taxaid_from_ancestor(con, ancid1)
                taxaids2 = get_taxaid_from_ancestor(con, ancid2)
                
                taxon_labels1 = []
                for t in taxaids1:
                    taxon_name = get_taxon_name(con, t)
                    taxon_labels1.append( taxon_name )
                
                taxon_labels2 = []
                for t in taxaids2:
                    taxon_name = get_taxon_name(con, t)
                    taxon_labels2.append( taxon_name )

                mrca1 = mltree.mrca(taxon_labels=taxon_labels1)
                mrca2 = mltree.mrca(taxon_labels=taxon_labels2)
                
                """Find the ancestor that is more descendant of the two ancestors."""
                if mrca1.level() < mrca2.level():
                    mrca2.label = "#1"
                else:
                    mrca1.label = "#1"
                labeled_tree = mltree.__str__()
                labeled_tree = re.sub("'", "", labeled_tree)
                                
                """Many different models of variable dN/dS"""
                dnds_models = ["M0", "M0_branch", "M0_branch_neutral", "M1a", "M2a", "Nsites", "Nsites_branch", "Nsites_branch_neutral"]
                
                for dnds_model in dnds_models:             
                    dnds_modelid = add_dnds_model(con, dnds_model)
                    
                    """Does the dN/dS test exist in the DB?"""
                    testid = add_dnds_test(con, msaid, modelid, ancid1, ancid2, dnds_modelid)
                    outdir = get_dnds_directory(con, testid)
                    
                    sql = "insert into LabeledDnDsPhylogenies (testid, newick) "
                    sql += " values(" + testid.__str__() + ",'" + labeled_tree.__str__() + "')"
                    cur.execute(sql)
                    con.commit()
                    
                    """Make a directory for the Codeml dN/dS work"""
                    dndsdir = get_dnds_directory(con, testid)
                    if False == os.path.exists(dndsdir):
                        os.system("mkdir " + dndsdir)
                    
                    """Put init. stuff in the working directory"""
                    phylippath = write_codeml_alignment(con, testid)
                    treepath = write_codeml_tree(con, testid)
                    controlpath = write_dnds_control_file(con, testid)
                    
                    runmepath = outdir + "/runme.sh"
                    fout = open(runmepath, "w")
                    fout.write("cd " + outdir + "\n")
                    fout.write(codeml_exe + " " + get_setting_values(con, "geneid" )[0] + ".ctl > catch.out\n")
                    fout.write("cd -\n")
                    fout.close()
 
                    commands.append("source " + runmepath)
    p = "SCRIPTS/dnds.commands.sh"
    fout = open(p, "w")
    for c in commands:
        fout.write( c + "\n")
    fout.close()
    return p

def get_dnds_directory(con, testid):
    cur = con.cursor()
    sql = "select almethod, phylomodel, anc1, anc2, dnds_model from DNDS_Tests where id=" + testid.__str__()
    cur.execute(sql)
    x = cur.fetchall()
    if x.__len__() == 0:
        return None
    almethod = x[0][0]
    sql = "select name from AlignmentMethods where id=" + almethod.__str__()
    cur.execute(sql)
    alname = cur.fetchone()[0]
    
    phylomodel = x[0][1]
    sql = "select name from PhyloModels where modelid=" + phylomodel.__str__()
    cur.execute(sql)
    phylomodelname = cur.fetchone()[0]
    
    ancid1 = x[0][2]
    sql = "select name from Ancestors where id=" + ancid1.__str__()
    cur.execute(sql)
    ancid1name = cur.fetchone()[0]
    
    ancid2 = x[0][3]
    sql = "select name from Ancestors where id=" + ancid2.__str__()
    cur.execute(sql)
    ancid2name = cur.fetchone()[0]
    
    dnds_model = x[0][4]
    sql = "select name from DNDS_Models where id=" + dnds_model.__str__()
    cur.execute(sql)
    dnds_modelname = cur.fetchone()[0]
    
    dndsdir = "dnds/dnds." + alname.__str__() + "." + phylomodelname.__str__() + "." + ancid1name.__str__() + "." + ancid2name.__str__() + "." + dnds_modelname.__str__()
    return dndsdir

def write_codeml_tree(con, testid):
    cur = con.cursor()
    
    sql = "select almethod, phylomodel, dnds_model from DNDS_Tests where id=" + testid.__str__()
    cur.execute(sql)
    x = cur.fetchone()
    almethod = x[0]
    phylomodel = x[1]
    dnds_modelid = x[2]
    sql = "select name from DNDS_Models where id=" + dnds_modelid.__str__()
    cur.execute(sql)
    dnds_model = cur.fetchone()[0]
    
    if dnds_model == "M0":
        sql = "select newick from UnsupportedMlPhylogenies where almethod=" + almethod.__str__() + " and phylomodelid=" + phylomodel.__str__()
    else:
        sql = "select newick from LabeledDnDsPhylogenies where testid=" + testid.__str__()
    cur.execute(sql)
    x = cur.fetchone()
    if x == None:
        return None
    newick = x[0] + ";"
    
    outdir = get_dnds_directory(con, testid)
    treepath = outdir + "/" + get_setting_values(con, "geneid" )[0] + ".tree"
    
    fout = open(treepath, "w")
    fout.write( newick + "\n")
    fout.close()
    return treepath

def write_codeml_alignment(con, testid):
    cur = con.cursor()    
    
    sql = "select almethod from DNDS_tests where id=" + testid.__str__()
    cur.execute(sql)
    x = cur.fetchone()
    if x == None:
        return None
    almethod = x[0]
    
    outdir = get_dnds_directory(con, testid)
    phylippath = outdir + "/" + get_setting_values(con, "geneid" )[0] + ".codons.phylip"
    
    """We want to write the seed taxon on top of the alignment. PAML will then report site scores
        relative to that seed sequence."""
    seedname = get_setting_values(con, "seedtaxa")[0]
    
    sql = "select taxonid, alsequence from AlignedSequences where almethod=" + almethod.__str__() + " and datatype=0"
    cur.execute(sql)
    x = cur.fetchall()
    seqs = {}
    
    #print seqs
    
    for ii in x:
        taxonid = ii[0]
        taxonname = get_taxon_name(con, taxonid)
        seq = ii[1]
        """Resolve uncertainties -- this is ugly, but PAML will fail otherwise."""
        seq = re.sub("R", "A", seq)
        seq = re.sub("Y", "C", seq)
        seq = re.sub("S", "G", seq)
        seq = re.sub("W", "A", seq)
        seq = re.sub("K", "G", seq)
        seq = re.sub("M", "A", seq)
        seq = re.sub("B", "C", seq)
        #seq = re.sub("-", "N", seq)
        seqs[ taxonname ] = seq
    write_phylip(con, seqs, phylippath, firstseq=seedname)
    return phylippath
    
def write_dnds_control_file(con, testid):
    cur = con.cursor()    
    sql = "select name from DNDS_Models where id in (select dnds_model from DNDS_Tests where id=" + testid.__str__() + ")"
    cur.execute(sql)
    x = cur.fetchall()
    if x == None:
        return None
    dnds_model = x[0][0]
    
    outdir = get_dnds_directory(con, testid)
    controlpath = outdir + "/" + get_setting_values(con, "geneid" )[0] + ".ctl"
    
    out = ""
    out += "seqfile = " + get_setting_values(con, "geneid" )[0] + ".codons.phylip\n"
    out += "treefile = " + get_setting_values(con, "geneid" )[0] + ".tree\n"
    out += "outfile = out.paml\n"
    out += "\n"
    out += "        noisy = 3\n"
    out += "      verbose = 0\n"
    out += "      runmode = 0\n"
    out += "\n"
    out += "      seqtype = 1  * 1:codons; 2:AAs; 3:codons-->AAs\n"
    out += "    CodonFreq = 2  * 0:1/61 each, 1:F1X4, 2:F3X4, 3:codon table\n"
    out += "        clock = 0   * 0:no clock, 1:global clock; 2:local clock; 3:TipDate\n"
    out += "       aaDist = 0  * 0:equal, +:geometric; -:linear, 1-6:G1974,Miyata,c,p,v,a\n"
    #out += "   aaRatefile = /../wag.dat\n"
    out += "\n"
    
    if dnds_model in ["M0", "M1a", "M2a", "Nsites"]:  
        out += "        model = 0\n"
    elif dnds_model in ["M0_branch", "M0_branch_neutral", "Nsites_branch", "Nsites_branch_neutral"]:
        out += "        model = 2\n"
    out += "                   * models for codons:\n"
    out += "                   * 0:one, 1:b, 2:2 or more dN/dS ratios for branches\n"
    out += "\n"
    
    if dnds_model in ["M0","M0_branch", "M0_branch_neutral"]:  
        out += "        NSsites = 0\n"
    elif dnds_model in ["M1a"]:  
        out += "        NSsites = 1\n"
    elif dnds_model in ["M2a", "Nsites","Nsites_branch", "Nsites_branch_neutral"]:
        out += "        NSsites = 2\n"
        
    out += "                   * 0:one w;1:neutral;2:selection; 3:discrete;4:freqs;\n"
    out += "                   * 5:gamma;6:2gamma;7:beta;8:beta&w;9:beta&gamma;\n"
    out += "                   * 10:beta&gamma+1; 11:beta&normal>1; 12:0&2normal>1;\n"
    out += "                   * 13:3normal>0;\n"
    out += "\n"
    out += "        icode = 0  * 0:universal code; 1:mammalian mt; 2-10:see below\n"
    
    out += "    fix_kappa = 0  * 1: kappa fixed, 0: kappa to be estimated\n"
    
    if dnds_model in ["M1a", "M2a"]:
        out += "        kappa = 0.3  * initial or fixed kappa\n"
    else:
        out += "        kappa = 2  * initial or fixed kappa\n"
    
    if dnds_model in ["sites_branch_neutral", "M0_branch_neutral"]:
        out += "    fix_omega = 1  * 1: omega or omega_1 fixed, 0: estimate \n"
    else:
        out += "    fix_omega = 0  * 1: omega or omega_1 fixed, 0: estimate \n"
    
    #if dnds_model in ["M1a", "M2a"]:
    #    out += "        omega = 1  * initial or fixed kappa\n"
    #else:
    out += "        omega = 1  * initial or fixed omega, for codons or codon-based AAs\n"
    
    out += "\n"
    out += "    fix_alpha = 1  * 0: estimate gamma shape parameter; 1: fix it at alpha\n"
    out += "        alpha = 0  * initial or fixed alpha, 0:infinity (constant rate)\n"
    out += "       Malpha = 0  * different alphas for genes\n"
    out += "        ncatG = 10  * # of categories in dG of NSsites models\n"
    out += "\n"
    out += "        getSE = 0  * 0: don't want them, 1: want S.E.s of estimates\n"
    out += " RateAncestor = 0  * (0,1,2): rates (alpha>0) or ancestral states (1 or 2)\n"
    out += "\n"
    out += "   Small_Diff = .5e-5\n"
    out += "   fix_blength = 2\n"
    out += "   cleandata = 0\n"
    
    fout = open(controlpath, "w")
    fout.write( out )
    fout.close()
    return controlpath


def parse_dnds_results(con):
    cur = con.cursor()
    
    sql = "delete from DNDS_lnL"
    cur.execute(sql)
    con.commit()
    sql = "delete from DNDS_BEB_sites"
    cur.execute(sql)
    con.commit()    
    sql = "delete from DNDS_params"
    cur.execute(sql)
    con.commit() 
    
    sql = "select id from DNDS_Tests"
    cur.execute(sql)
    x = cur.fetchall()
    for ii in x:
        testid = ii[0]
        outdir = get_dnds_directory(con, testid)
        
        """Get the likelihood.
        If we encounter errors, just continue to the next dN/dS folder"""
        catchpath = outdir + "/catch.out"
        if False == os.path.exists( catchpath ):
            write_error(con, "I cannot find dN/dS output in the folder " + outdir)
            continue
        fin = open(catchpath, "r")
        lnl = None
        for l in fin.xreadlines():
            if l.startswith("lnL"):
                lnl = float( l.split()[2] )
        if lnl == None:
            write_error(con, "I couldn't find lnL value in the PAML output " + catchpath)
            continue
        
        #write_log(con, outdir + " Log-Likelihood = " + lnl.__str__())
        
        sql = "insert into DNDS_lnL(testid, lnl) values(" + testid.__str__() + "," + lnl.__str__() + ")"
        cur.execute(sql)
        con.commit()
        
        sql = "select name from DNDS_Models where id in (select dnds_model from DNDS_Tests where id=" + testid.__str__() + ")"
        cur.execute(sql)
        dnds_model = cur.fetchone()[0]
        
        """Get the omega values."""
        outpath = outdir + "/out.paml"
        if False == os.path.exists( outpath ):
            write_error(con, "I cannot find dN/dS output file " + outpath)
            exit()
        pclass1 = -1.0
        pclass2 = -1.0
        pclass3 = -1.0
        pclass4 = -1.0
        wclass1 = -1.0
        wclass2 = -1.0
        wclass3 = -1.0
        wclass4 = -1.0
        
        fin = open(outpath, "r")
        for l in fin.xreadlines():
            if l.startswith("p:"):
                tokens = l.split()
                pclass1 = float( tokens[1] )
                pclass2 = float( tokens[2] )
                if tokens.__len__() > 3:
                    pclass3 = float( tokens[3] )        
            if l.startswith("p:"):
                tokens = l.split()
                wclass1 = float( tokens[1] )
                wclass2 = float( tokens[2] )
                if tokens.__len__() > 3:
                    wclass3 = float( tokens[3] ) 
            if l.startswith("proportion"):
                tokens = l.split()
                pclass1 = float( tokens[1] )
                pclass2 = float( tokens[2] )
                pclass3 = float( tokens[3] )        
                pclass4 = float( tokens[4] ) 
            if l.startswith("foreground w"):
                tokens = l.split()
                wclass1 = float( tokens[2] )
                wclass2 = float( tokens[3] )
                wclass3 = float( tokens[4] ) 
                wclass4 = float( tokens[5] )
        sql = "insert into DNDS_params (testid, pclass1, pclass2, pclass3, pclass4, wclass1, wclass2, wclass3, wclass4)"
        sql += " values(" + testid.__str__() + "," + pclass1.__str__() + "," + pclass2.__str__() + "," + pclass3.__str__() + "," + pclass4.__str__()
        sql += "," + wclass1.__str__() + "," + wclass2.__str__() + "," + wclass3.__str__() + "," + wclass4.__str__() + ")"
        cur.execute(sql)
        con.commit()
        fin.close()
        
#         sql = "select * from DNDS_params where testid=" + testid.__str__()
#         cur.execute(sql)
#         params = cur.fetchone()
        #write_log(con, "I found these param. results in " + outdir + ": " + params.__str__() )
        
        """If its a sites model, get the per-site BEB scores from the PAML rst file."""
        if dnds_model.__contains__("sites"):
            rstpath = outdir + "/rst"
            if False == os.path.exists(rstpath):
                write_error(con, "I cannot find the rst file from codeml at " + rstpath)
                exit()
            fin = open(rstpath, "r")
   
            
            contains_beb = False
            contains_neb = False
            found_beb = False
            found_neb = False
            lines = fin.readlines()
            for l in lines:
                if l.__contains__("BEB"):
                    contains_beb = True
                if l.__contains__("NEB"):
                    contains_neb = True

            expected_columns = None
            found1 = False
            for l in lines:
                #print l
                if l.__contains__("BEB"):
                    found_beb = True
                if l.__contains__("NEB"):
                    found_neb = True
                                                
               # if l.startswith(" ") or l.startswith("lnL"):
               #    found1 = False    
               #     continue
                

                if found1 == False and (contains_beb == True and found_beb == True) or (contains_beb == False and contains_neb == True and found_neb == True):
                    if l.__len__() > 2:
                        tokens = l.split()
                        site = re.sub(" ", "", tokens[0])
                        if site.startswith("1"):
                            found1 = True
                            expected_columns = tokens.__len__()
                                                                
                if found1 == True:
                    tokens = l.split()
                    if tokens.__len__() == expected_columns:
                        site = int( re.sub(" ", "", tokens[0]) )
                        p1 = -1
                        p2 = -2
                        p3 = -1
                        p4 = -1
                        p1 = float( re.sub("\*", "", tokens[2]) )
                        p2 = float( re.sub("\*", "", tokens[3]) )
                        if False == tokens[4].startswith("(") and False == tokens[4].startswith("+"):
                            p3 = float( re.sub("\*", "", tokens[4]) )
                        if tokens.__len__() > 5:
                            if False == tokens[5].startswith("(") and False == tokens[5].startswith("+"):
                                p4 = float( re.sub("\*", "", tokens[5] ) )
                        if p1 > 1 or p2 > 1 or p3 > 1 or p4 > 1:
                            write_error(con, "probability cannot exceed 1.0 Error 444")
                            print rstpath
                            print l
                            exit()
                        
                        sql = "insert into DNDS_BEB_sites (testid, site, ppcat1, ppcat2, ppcat3, ppcat4)"
                        sql += " values(" + testid.__str__() + "," + site.__str__()
                        sql += "," + p1.__str__() + "," + p2.__str__() + "," + p3.__str__() + "," + p4.__str__() + ")"
                        cur.execute(sql)
                        con.commit()
            fin.close()
        
            sql = "select count(*) from DNDS_BEB_sites where testid=" + testid.__str__()
            cur.execute(sql)
            count = cur.fetchone()[0]
            write_log(con, "I found " + count.__str__() + " BEB sites in " + outdir)
            

def setup_compare_functional_loci(con):
    cur = con.cursor()
    
    sql = "delete from Compare_DNDS_Fscores"
    cur.execute(sql)
    con.commit()
    
    sql = "select id from DNDS_Models where name='Nsites_branch'"
    cur.execute(sql)
    nsites_id = cur.fetchone()[0]
    
    sql = "select id from AlignmentMethods where name='mafft'"
    cur.execute(sql)
    mafftid = cur.fetchone()[0]
    ml_modelid = get_ml_model(con, mafftid)
    
    sql = "select id, almethod, anc1, anc2 from DNDS_Tests where dnds_model=" + nsites_id.__str__() + " and phylomodel=" + ml_modelid.__str__()
    cur.execute(sql)
    x = cur.fetchall()
    for ii in x:
        dnds_testid = ii[0]
        almethod = ii[1]
        phylomodel = ml_modelid
        anc1 = ii[2]
        anc2 = ii[3]
        
        """Find the matching Fscore test"""
        sql = "select id from FScore_Tests where almethod=" + almethod.__str__() + " and phylomodel=" + phylomodel.__str__() + " and ancid1=" + anc1.__str__() + " and ancid2=" + anc2.__str__()
        cur.execute(sql)
        y = cur.fetchall()
        if y.__len__() > 0:
            fscore_testid = y[0][0]
            
            sql = "insert into Compare_DNDS_Fscores (dnds_testid, fscore_testid) values(" + dnds_testid.__str__()
            sql += "," + fscore_testid.__str__() + ")"
            cur.execute(sql)
            con.commit()

def compare_functional_loci(con):
    cur = con.cursor()
    sql = "select dnds_testid, fscore_testid from Compare_DNDS_Fscores"
    cur.execute(sql)
    x = cur.fetchall()
    
    fout = open("compare_dnds_Df.txt", "w")
    
    for ii in x:
        dnds_testid = ii[0]
        fscore_testid = ii[1]
        
        """Get scores for sites."""
        site_ppcat2 = {}
        site_ppcat3 = {}
        site_ppcat4 = {}
        site_df = {}
        site_k = {}
        site_p = {}
        
        sql = "select site, ppcat1, ppcat2, ppcat3, ppcat4 from DNDS_BEB_sites where testid=" + dnds_testid.__str__()
        cur.execute(sql)
        qq = cur.fetchall()
        for jj in qq:
            site_ppcat2[ jj[0] ] = jj[2] 
            site_ppcat3[ jj[0] ] = jj[3]
            site_ppcat4[ jj[0] ] = jj[4]
        
        sql = "select site, df, k, p from FScore_Sites where testid=" + fscore_testid.__str__()
        cur.execute(sql)
        qq = cur.fetchall()
        for jj in qq:
            site_df[ jj[0] ] = jj[1] 
            site_k[ jj[0] ] = jj[2]
            site_p[ jj[0] ] = jj[3]
        
        dnds_sites = site_ppcat2.keys()
        df_sites = site_df.keys()
        sites = []
        for s in dnds_sites:
            if s in df_sites:
                sites.append(s)
            #else:
                #print "Site ", s, "not in Df"
            
        print "\n. " + sites.__len__().__str__() + " sites have scores for both Df and dN/dS."   
        print "\n. " + (dnds_sites.__len__()-sites.__len__()).__str__() + " do not match." 
        sites.sort()
        for s in sites:
            line = s.__str__() + "\t" + site_ppcat2[s].__str__() + "\t" +  site_ppcat3[s].__str__() + "\t" + site_ppcat4[s].__str__() + "\t" + site_df[s].__str__() + "\t" + site_k[s].__str__() + "\t" + site_p[s].__str__()
            fout.write(line + "\n")
            
    fout.close()
    
    
    
    