#!/usr/bin/env python
# coding: utf-8

# # Analyse votes Constituante
# Version 07.11.2020

# In[1]:


import os,sys,getopt
import pandas as pd
import xlrd
from datetime import datetime

#### TODO : separate data preparation part (extracting data from xls crappy files into clean csv)
#### from analysis part, which sould rely on clean CSV files
#### 


### 
### RATHER USE AS STANDALONE SCRIPT WITH ARGUMENTS 
#
# python votes-analysis.py -i <inputdir> -o <outputdir> -m <mappingfile>
#
# in <inputdir>, will parse all 'Vote*.xlsx' files ( * = wildcard )
# in <outputdir>, will generate csv files
#
###
## time spent : 3h (at 20:30)
## time spent : 5h (at 22:30)
## time spent : 1h30 (14.5.2019 - 10h30)

################
IN_DIR = './All Votes' ## directory containing Excel files
IN_MAP = 'Constituante-Ref-2020.10.csv' ## mapping files with corresponding names + attributes (encoded as iso-8859-1)
OUT_DIR = './All Votes - analyse'
OUT_DETAILS_DIR = './All Votes - analyse/details'
OUT_VOTES = 'All_votes.csv'
OUT_META = 'All_votes_metadata.csv'
OUT_GROUP_MAJ = 'All-votes-group-majorities-ai.csv'
OUT_GROUP_MAJ_DETAILS = 'All-votes-group-majorities-details.csv'
OUT_VOTES_DETAILS = "All_votes_details.csv"
OUT_VOTES_SWINGERS = "All-votes-swingers.csv"
##################
    
def main(argv):
    global IN_DIR
    global OUT_DIR 
    global IN_MAP
    try:
        opts, args = getopt.getopt(argv,"hi:o:m:",["ifile=","ofile=","mfile="])
    except getopt.GetoptError:
        print ('get-votes.py -i <inputdir> -o <outputdir> -m <mappingfile>')
        print('Defaults:')
        print('<inputdir> = '+IN_DIR)
        print('<outputdir> = '+OUT_DIR)
        print('<mappingfile>' +IN_MAP)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print ('get-votes.py -i <inputdir> -o <outputdir> -m <mappingfile>')
            sys.exit()
        elif opt in ("-i", "--ifile"):
            IN_DIR = arg
        elif opt in ("-o", "--ofile"):
            OUT_DIR = arg
        elif opt in ("-m", "--mfile"):
            IN_MAP= arg

# execute only if run as a script ( !!! uncomment if exported)
if __name__ == "__main__":
    main(sys.argv[1:])

####################
# Makedirs if don't exist

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(OUT_DETAILS_DIR, exist_ok=True)


# In[2]:


# Import list of all votes + mapping file
## List all excel files
votesFiles = []
for file in os.listdir(IN_DIR):
    if file.endswith(".xls") and file.startswith("Vote"):
        votesFiles.append(os.path.join(IN_DIR,file))

## Mapping file
mapping = pd.read_csv(IN_MAP)
#mapping.head()


# In[4]:


#votesFiles


# In[3]:


# Reads vote metadata from Excel
def getVoteMetaData(file):
    workbook = xlrd.open_workbook(file)
    worksheet = workbook.sheet_by_name('Sheet1')
    dateformat = "%d.%m.%Y %H:%M:%S"
    startTime = datetime.strptime(worksheet.cell(2, 1).value,dateformat)
    endTime = datetime.strptime(worksheet.cell(3, 1).value,dateformat)
    affairVoteId = startTime.strftime("%Y%m%d%H%M%S")
    label = worksheet.cell(4, 1).value
    numYes = int(worksheet.cell(11, 2).value)
    numNo = int(worksheet.cell(12, 2).value)
    numAbst = int(worksheet.cell(13, 2).value)
    meaningYes = "Accepter"
    meaningNo = "Refuser"
    if "<>" in label:
        s = label.split("<")
        meaningYes = s[0].strip()
        meaningNo = s[1][1:].strip()
    return {
        "filename": os.path.basename(file),
        "startTime": startTime,
        "endTime": endTime,
        "label": worksheet.cell(4, 1).value,
        "affairVoteId":affairVoteId,
        "meaningYes": meaningYes,
        "meaningNo" : meaningNo,
        "meaningYesText": "",
        "meaningNoText" : "",
        "numYes": numYes,
        "numNo": numNo,
        "numAbst": numAbst,
        "affair" : "",
        "section":"",
        "note":"",
        "warning":"",
        "linkVideo":"",
        "attachment":""
    }

# Reads raw votes from Excel
def readRawVotes(file):
    df = pd.read_excel(file,usecols=[1,2,3],skiprows=28)
    df.columns=["name","group","vote"]
    return df

# fix groups in df due to technical problem in voting system. => Based on name, retrieve group from mapping_file which is correct
def fixGroups(votesDf):
    votesDf["group"] = votesDf['name'].map(lambda name: (mapping[mapping["nom_corresp_vote"]==name]["Groupe (abbreviation)"]).iloc[0])
    return votesDf
    
# Reads raw votes + add missing names (people who did not vote) + join additional metadata
def getAllVotes(file):
    raw = readRawVotes(file)
    maps = mapping["nom_corresp_vote"]
    notvoted = mapping[~maps.isin(raw["name"])]
    toadd = []
    for index, row in notvoted.iterrows():
        toadd.append({
            "name":row["nom_corresp_vote"],
            "group":row["Groupe (abbreviation)"],
            "vote":"Aucun/Keine"
        })
    df = pd.DataFrame.from_dict(toadd)
    full = raw.append(df,ignore_index=True)
    columnstokeep = [mapping.columns[i] for i in [4,5,7,11]]
    maps = mapping[columnstokeep].set_index("nom_corresp_vote")
    complete = full.join(maps, on="name", how="inner")
    fixed = fixGroups(complete) #### ADDED SEPTEMBER 2020 TO CORRECT WRONG GROUP ATTRIBUTION
    return fixed


def getAllVotesFromList(filesList):
    votes = None
    metadata = []
    for f in filesList:
        print("Handling file : "+f)
        try:
            metadatum = getVoteMetaData(f)
            metadata.append(metadatum)
            vote = getAllVotes(f)
            vote["affairVoteId"] = metadatum["affairVoteId"]
            if votes is None:
                votes = vote
            else:
                votes = votes.append(vote, ignore_index=True)
            print("Votes inserted : "+str(len(vote.index)))
            print("Total votes size : "+str(len(votes.index)))
        except:
            print("Error ! File ignored")
    return metadata, votes


# In[4]:


## get all the data
metadata, votes = getAllVotesFromList(votesFiles)


# In[5]:


metadf = pd.DataFrame.from_dict(metadata)
#metadf.head()


# In[6]:


#votes.head()


# In[7]:


# output everything to csv, sorted chronologically (affairVoteId is built on date & time of vote)
metadf.sort_values(by=['affairVoteId']).to_csv(os.path.join(OUT_DIR,OUT_META))
votes.to_csv(os.path.join(OUT_DIR,OUT_VOTES))


# In[8]:


#votes


# In[8]:


# extraire chaque vote dans son fichier individuel avec affairevoteid comme titre
for affairVoteId in votes['affairVoteId'].unique():
    votes[votes['affairVoteId']==affairVoteId].to_csv(os.path.join(OUT_DETAILS_DIR,str(affairVoteId)+".csv"), index=False)




