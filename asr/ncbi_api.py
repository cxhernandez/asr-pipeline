"""A collection of methods to query NCBI."""


from Bio import Blast
from Bio.Blast import NCBIWWW


def aa_to_mrna(aaseq):
    """Given an amino acid sequence, return the mRNA sequence, if it exists,
        from the NCBI nucleotide database."""
    result_handle = NCBIWWW.qblast("tblastn", "nr", aaseq, descriptions=10)
    result = result_handle.read()
    print result
    return result

# from Bio.Blast import NCBIWWW
# result_handle=NCBIWWW.qblast('blastn', 'nt', 'AGAAAGGGTATATAAAATCAAGAATCTGGGGTGTTTGTGTTGACTTGTATAATTCTTGATTTTTTCAGGTAGTTGAAAAGGTGGGAGAAAAGTGGAGAAGCCTAAGCTGATATTGAAATTCATATGGATGGAAGAACATTGGTTTAGGATTGGATCAAAAAATAGGTGGACATGGAACTGTA')
# print result_handle

aa_to_mrna("MPPTKTQTHPDIQPVTEDRRSLTVKSLDDRYVLLKNIGKGSFGHVSLARVRSKAAMENEDMRAGSMVAIKTMKKKLAAIDDYNLLREVEFIREVRPHRFLVNVHDMFVDSVNHHFHMSMEVMEMNLYNLMKAQEKVPFQPHAVRSMLWQIICGIDHIHRHNFFHRDIKPENILVSRYLPYHNENSSSPHSGFRIKIADFGLSRHIEDRDPYTAYVSTRWYRAPEILLRCEYYSAPVDIWAFGAMAAEVANLKPLFPGTNELDQFSLQVALLGTPGQNSLGGRWSRHPELCSKLNINIDAQTGQSSNSIMCNPEHASLTDVVLMCLTWDPDARCSARDIMYHRYFAQESSIEVPRTLKRSPLRITKQAAMNPHGDPPILMDPSLRHNNSNANNSAIVPTLASSLKQNQGLQMNKSHLSGVNGSTKRNSLSGAAAAAAMSMSLSLASKNSSVNSGGAGFLAGAAPAKKKFGHWANIFKRDSDVASSELERVGPNKENVPSIVPTQTPNRGAGGVGIVPKIPLPQLPPLETIAASIESLSIEARSTNTTLTERMTSGPPTGGTSDSEWSTTNASISESVGHDSGAGSSGAVDKGSTGTTNFEVEALMESTEARVTVKTLPQTPDSASSYDQMPPPPLPLPKVRVTAKPLNAIKPESPTQVQVSLSPQPCIKPPSPASSHYEPPACLDEHSDSQLTAYERSVRDSVLLMSFTLPPSSQESCTSLEGASESPSVNDSPLVDQFGGSSSDIRIETTSFLTPDLDKGNVWVRSEELECPVYPGLQTNSFRDRKIGAGAISSNNIEVE")
