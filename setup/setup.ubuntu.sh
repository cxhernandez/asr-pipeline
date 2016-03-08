##############################################################
#
# This shell script will install all the dependent software
# necessary to run the ASR Pipeline
#
##############################################################

export ASR_PIPELINE_DIR=$HOME/asr-pipeline/
export COMMON=$HOME/common/

cd $HOME
wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh && \
chmod +x Miniconda3-latest-Linux-x86_64.sh
./Miniconda3-latest-Linux-x86_64.sh

conda create -y --name=asr-pipeline python=2.7 numpy scipy biopython
source activate asr-pipeline


DONT_USE_PYREX=1
pip install -r $ASR_PIPELINE_DIR/requirements.txt

mkdir -p $COMMON

# MUSCLE
####################
curl -O http://www.drive5.com/muscle/downloads33/muscle_3.3_src.tar.gz
mv muscle3.3_src.tar.gz $COMMON
cd $COMMON
gzip -d muscle3.3_src.tar.gz
tar -xvf muscle3.3_src.tar
cd muscle
make
export PATH=$COMMON/muscle/:$PATH
cd /

# MSAPROBS
###############
cp $ASR_PIPELINE_DIR/apps/MSAProbs-0.9.7.tar $COMMON
cd $COMMON
tar -xvf MSAProbs-0.9.7.tar
cd MSAProbs-0.9.7/MSAProbs/
make
export PATH=$COMMON/MSAProbs-0.9.7/MSAProbs/:$PATH
cd /

# PHYML
################
#curl -O https://github.com/stephaneguindon/phyml-downloads/releases/download/stable/phyml-20120412.tar.gz
#mv phyml-20120412.tar.gz /common/
cp $ASR_PIPELINE_DIR/apps/phyml-20120412.tar /common/
cd /common
#gzip -d phyml-20120412.tar.gz
tar -xvf phyml-20120412.tar
cd phyml-20120412
./configure
make
export PATH=$COMMON/phyml-20120412/src/:$PATH
cd /

#
# RAxML
#
cd $COMMON
git clone git://github.com/stamatak/standard-RAxML.git
cd standard-RAxML/
make -f Makefile.PTHREADS.gcc
ln -s $COMMON/standard-RAxML/raxmlHPC-PTHREADS $COMMON/standard-RAxML/raxml
export PATH=$COMMON/standard-RAxML/:$PATH


# LAZARUS
cd $COMMON
git clone https://project-lazarus.googlecode.com/git lazarus

# PAML
cd $COMMON/lazarus/paml/src
make
cd /
export PATH=$COMMON/lazarus/paml/src/:$PATH

# R
sudo apt-get install r-base
export PATH=/usr/bin/R:$PATH

cd $ASR_PIPELINE_DIR
python setup.py install
