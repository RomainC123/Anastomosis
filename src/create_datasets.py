import os
import re
import random
from constants import *

import pandas as pd

import json

from tqdm.auto import tqdm

sentences_full_list = []
labels_full_list = []

with open(os.path.join(ROOT_PATH, "data", "2021AB_SN", "SRSTRE1")) as f:
    umls_relations_df = pd.read_csv(f, delimiter='|', names=["FirstTUI", "RelationTUI", "EndTUI"], index_col=False)

with open(os.path.join(ROOT_PATH, "data", "2021AB_SN", "SRDEF"), "r") as f:
    def_df = pd.read_csv(f, delimiter="|", header=None)
relation_def_df = def_df.loc[def_df[0] == "RL"].reset_index(drop=True)

for filename in tqdm(os.listdir(RELATIONS_PATH)):

    with open(os.path.join(DATA_CLEAN_PATH, filename.split("_")[0] + ".txt"), "r") as f:
        text = f.read()

    with open(os.path.join(ENTITIES_PATH, filename.split("_")[0] + ".csv"), "r") as f:
        entities_df = pd.read_csv(f).drop("Unnamed: 0", axis=1)

    with open(os.path.join(RELATIONS_PATH, filename), "r") as f:
        relations_df = pd.read_csv(f).drop("Unnamed: 0", axis=1)

    sentences = []

    cursor = 0
    last_end = 0

    for word, start_char, end_char in list(entities_df[["Word", "StartChar", "EndChar"]].itertuples(index=False, name=None)):
        dot = re.search("\.", text[cursor:start_char])
        if dot:
            sentences.append({"Text": text[last_end:cursor + dot.span()[0]],
                              "StartChar": last_end,
                              "EndChar": cursor + dot.span()[0]})
            last_end = cursor + dot.span()[1]
        else:
            pass
        cursor = end_char
    sentences_df = pd.DataFrame(sentences)

    for first_id, second_id, first_word, second_word, first_tui, second_tui in list(relations_df[["First", "End", "FirstWord", "EndWord", "FirstTUI", "EndTUI"]].itertuples(index=False, name=None)):
        sent_id = entities_df.iloc[first_id]["Sentence"]
        if sent_id not in sentences_df.index:
            continue
        sent_text = sentences_df.iloc[sent_id]["Text"]
        sent_start = sentences_df.iloc[sent_id]["StartChar"]
        sent_end = sentences_df.iloc[sent_id]["EndChar"]

        first_start_char = entities_df.iloc[first_id]["StartChar"]
        first_end_char = entities_df.iloc[first_id]["EndChar"]
        second_start_char = entities_df.iloc[second_id]["StartChar"]
        second_end_char = entities_df.iloc[second_id]["EndChar"]

        sentence_full = "[CLS] " + sent_text[:first_start_char - sent_start].strip() + \
                        " <e1>" + str(first_word) + "</e1>" + \
                        sent_text[first_end_char - sent_start:second_start_char - sent_start] + \
                        "<e2>" + str(second_word) + "</e2> " + \
                        sent_text[second_end_char - sent_start:].strip() + " [SEP]"
        sentences_full_list.append(sentence_full)

        if first_tui and second_tui:
            possible_labels = umls_relations_df["RelationTUI"].loc[umls_relations_df["FirstTUI"]
                                                                   == first_tui].loc[umls_relations_df["EndTUI"] == second_tui]
            if len(possible_labels) > 0:
                label_TUI = random.choice(possible_labels.values)
                label = int(relation_def_df.loc[relation_def_df[1] == label_TUI].index[0] + 1)
            else:
                label = 0
        else:
            label = 0
        labels_full_list.append(label)

json_object_sentences = json.dumps(sentences_full_list)
json_object_labels = json.dumps(labels_full_list)

with open("train_sentences.json", "w") as f:
    f.write(json_object_sentences)

with open("train_label_id.json", "w") as f:
    f.write(json_object_labels)
