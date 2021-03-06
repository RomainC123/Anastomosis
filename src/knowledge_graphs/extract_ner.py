import os

import re
import spacy
import pandas as pd

from tqdm.auto import tqdm

from .manual_models import names_et_al

from constants import *


def get_entities_from_spacy(text, model, name, filename):

    doc = model(text)
    entities = list(doc.ents)
    entities.sort(key=lambda x: x.start_char)

    entities_list = []
    try:
        linker = model.get_pipe("scispacy_linker")
    except:
        linker = None

    for ent in entities:
        word = ent.lemma_
        e_type = ent.label_
        source = name
        start_char = ent.start_char
        end_char = ent.end_char
        document = filename.split('.')[0]
        try:
            CUI, score = ent._.kb_ents[0]
        except:
            CUI, score = None, None
        if CUI and score:
            TUI = re.search(r"T[0-9]{3}", str(linker.kb.cui_to_entity[CUI]))[0]
            group = TUI_MAP[TUI]
        else:
            TUI, group = None, None

        entities_list.append({"Word": word,
                              "Type": e_type,
                              "Source": source,
                              "StartChar": start_char,
                              "EndChar": end_char,
                              "Document": document,
                              "CUI": CUI,
                              "Score": score,
                              "TUI": TUI,
                              "Group": group})

    return entities_list


def get_entities_from_manual(text, model, name, filename):

    words_list = model(text)

    entities_list = []

    for word in words_list:
        e_type = "PERSON"
        source = name
        start_char, end_char = re.search(word, text).span()
        document = filename.split('.')[0]
        entities_list.append({"Word": word,
                             "Type": e_type,
                              "Source": source,
                              "StartChar": start_char,
                              "EndChar": end_char,
                              "Document": document})

    entities_list.sort(key=lambda x: x["StartChar"])
    return entities_list


def build_merged_entities_df(filename, ner_models):

    with open(os.path.join(DATA_CLEAN_PATH, filename), "r") as f:
        text = f.read()

    entities_df = pd.DataFrame()
    seen = [0] * len(text)

    for model in ner_models:
        model_type = model["type"]
        model_name = model["name"]
        model_prio = model["prio"]
        model_nlp = model["model"]
        if model_type == "Spacy":
            entities_list = get_entities_from_spacy(text, model_nlp, model_name, filename)
        elif model_type == "Manual":
            entities_list = get_entities_from_manual(text, model_nlp, model_name, filename)
        else:
            raise NotImplementedError(f"Model type {model_type} is unknown.")

        if len(entities_df) > 0:
            good_entities = []
            for ent in entities_list:
                if sum(seen[ent["StartChar"]:ent["EndChar"]]) == 0:
                    good_entities.append(ent)
                    seen[ent["StartChar"]:ent["EndChar"]] = [1] * (ent["EndChar"] - ent["StartChar"])
            entities_df = pd.concat([entities_df, pd.DataFrame(good_entities)])
        else:
            for ent in entities_list:
                seen[ent["StartChar"]:ent["EndChar"]] = [1] * (ent["EndChar"] - ent["StartChar"])
            entities_df = pd.DataFrame(entities_list)

    if len(entities_df) != 0:
        entities_df = entities_df.sort_values(by=["Document", "StartChar"], axis=0).reset_index(drop=True)

    text = re.sub("[^a-zA-Z0-9\.]", " ", text)

    if len(entities_df) > 0:
        cursor = 0
        cnt_words = 0
        cnt_sentences = 0
        words_dicts = []
        for word, start_char, end_char in list(entities_df[["Word", "StartChar", "EndChar"]].itertuples(index=False, name=None)):
            cnt_words += sum([len(a) > 0 for a in text[cursor:start_char].split(" ")])
            cnt_sentences += sum([a == "." for a in text[cursor:start_char]])
            start_id = cnt_words
            sentence_id = cnt_sentences
            num_words = sum([len(a) > 0 for a in word.split(" ")])
            end_id = start_id + num_words - 1
            cnt_words += num_words
            words_dicts.append({"Word": word, "StartWord": start_id, "EndWord": end_id, "Sentence": sentence_id})
            cursor = end_char
        words_df = pd.DataFrame(words_dicts)

        entities_df = pd.concat([entities_df, words_df[["StartWord", "EndWord", "Sentence"]]], axis=1)

    return entities_df
