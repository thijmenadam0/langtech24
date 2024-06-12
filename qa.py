#
#
#
#

import requests
import re
import spacy
import json
from time import sleep


def phrase(word):
    '''
    This function takes a noun, collects the corresponding
    to the noun children in the sentence, combines them in
    a noun phrase and returns as a string
    '''
    special_adjectives = {
        'vrouwelijke': ['vrouwelijk organisme', 'sekse of geslacht'],
        'mannelijke': ['mannelijk organisme', 'sekse of geslacht'],
    }
    ent_2 = ''
    prop_2 = ''
    children = []
    for child in word.subtree :
        if child.text not in special_adjectives:
            if child.dep_ != 'cop' and child.dep_ != 'nmod:poss': # get rid of words 'zijn' and 'is'
                if word.dep_ == 'ROOT' or word.dep_ == 'nsubj':
                    # allow only adj and det to be added to the root noun phrase
                    if child.pos_ == 'ADJ' or child.dep_ == 'amod':  # amod for 'bedreigde diersoort'
                        children.append(child.text)
                    elif child.text == word.text:
                        children.append(child.lemma_)
                    if child.text == 'leeuwen' and word.pos_ != 'NOUN':
                        children = ['leeuwen']
                else:
                    children.append(child.text)
        else:
            ent_2 = special_adjectives[child.text][0]
            prop_2 = special_adjectives[child.text][1]
    result = " ".join(children)
    result = re.sub(r'^(van |tot )', '', result) # remove cases of noun phrases like 'van een kat' 'tot de familie...'
    result = re.sub(r'^(alle )', '', result) # remove cases of noun phrases like 'alle soorten katten'.

    result = re.sub(r'(per keer)', '', result) # remove cases of noun phrases like 'eieren per keer''
    if ent_2 == '':
        return re.sub(r'^(de |het |een )', '', result)
    else:
        return re.sub(r'^(de |het |een )', '', result), ent_2, prop_2


def word_change(word, is_waar=False):
    '''Changes a word to a word that wikidata understand'''

    prop_words = {
        'groot': 'hoogte',
        'hoog': 'hoogte',
        'lang': 'hoogte',
        'oud': 'levensverwachting',
        'leven': 'levensverwachting',
        'zwaar': 'gewicht',
        'wegen': 'gewicht',
        'heten': 'naam',
        'soort': 'subklasse van',
        'eten' : 'belangrijkste voedselbron',
        'zwanger' : 'draagtijd'
    }

    noun_words = {
        'ei' : 'nestgrootte',
        # SpaCy thinks the lemma of eitjes is eit
        'eit' : 'nestgrootte',
        'kind' : 'nestgrootte',
        'reuzentoekans': 'reuzentoekan',
        "kiwi's" : 'kiwi',
        'kangeroe' : 'kangoeroes',
        'pinguin' : 'pinguins',
        'Leeuwen' : 'leeuw'
    }

    root_words = {
        'vinden' : ['habitat', 'endemisch in'],
        'leven' : ['habitat', 'endemisch in'],
        'komen vandaan' : ['habitat', 'endemisch in'],
        'komen voor' : ['habitat', 'endemisch in'],
        'goed voor' : ['gebruik']
    }

    if word in prop_words and not is_waar:
        return prop_words[word]
    
    elif word in noun_words:
        return noun_words[word]

    elif word in root_words and is_waar:
        return root_words[word]

    else:
        return word


def welke_questions(parse):
    '''This function makes it so it returns the entity and property
    words for questions sarting with 'welke'
    '''
    entity_word = ""
    property_word = ""
    for word in parse:
        if word.dep_ == 'nsubj':
            entity_word = phrase(word)
        elif word.dep_ == 'obj':
            property_word = word.lemma_

    return entity_word, property_word


def waar_questions(parse):
    '''This function makes it so it returns the entity and property
    words for questions sarting with 'waar'
    '''

    for word in parse:
        if word.pos_ == 'NOUN':
            entity_word = phrase(word)

        elif word.dep_ == 'ROOT' and (word.pos_ == 'VERB' or word.pos_ == 'ADJ'):
            for child in word.subtree:
                # print(child.text, child.pos_, child.dep_)
                if child.pos_ == 'ADP' and (child.dep_ == 'obl' or child.dep_ == 'compound:prt'):
                    property_word = word.lemma_ + ' ' + child.text
                elif child.pos_ == 'NOUN' and child.dep_ == 'nsubj':
                    property_word = word.lemma_

    # print(entity_word, property_word)

    return entity_word, property_word

def hoe_questions(parse):
    '''This function makes it so it returns the entity and property
    words for questions sarting with 'hoe'
    '''
    h = False
    if str(parse[0]) == 'hoeveel' or str(parse[0]) == 'Hoeveel':
        if parse[1].pos_ == 'NOUN':
            h = True
    for word in parse:
        if word.pos_ == 'NOUN' and (word.dep_ == 'nsubj' or word.dep_ == 'obj'): # TODO: find out why I added word.dep_ in the first place
            # entity_word = word.lemma_
            entity_word = phrase(word)

        elif word.dep_ == "ROOT" and (word.pos_ == 'ADJ' or word.pos_ == 'VERB') or word.dep_ == 'parataxis':
            property_word = word.lemma_
    
    # Hebben, leggen and zijn are auxiliaries, they are never property words.
    if property_word == 'leggen' or property_word == 'hebben' or property_word == 'zijn':
        for word in parse:
            if word.pos_ == 'NOUN' and word.dep_ == 'nsubj':
                property_word = word.lemma_
                break # Because we need the first one, as that is how Dutch questions are posed.
    return entity_word, property_word, h


def janee_questions(parse, is_behoort, verb_lemma=''):

    '''
    This function takes a sentence parse, takes the necessary
    noun phrases from it and assigns them to the variables,
    then returns them as strings
    '''

    verb_dict= {
        'eten' : 'belangrijkste voedselbron',
        'Hebben' : 'omvat deel', # spacy does not
        # 'Heeft' : 'omvat deel',  # recognize them as verbs
    }

    property_word = ""
    noun_phrases = []
    if verb_lemma:
        property_word = verb_dict[verb_lemma]
    for word in parse:
        # print(word, word.pos_, word.dep_)
        if word.pos_ == 'NOUN':
            # ensure lemmatization, except for if the word is plant
            # as wiktionary can only handle the word 'planten'
            w_phrase = phrase(word)
            w_lemma = word.lemma_
            if ' ' in w_phrase:
                for w in w_phrase.split():
                    if w.startswith('w_lemma'):
                        w_phrase.replace(w, w_lemma)
            else:
                w_phrase = w_lemma
                if w_phrase == 'plant':
                    w_phrase = 'planten'
            noun_phrases.append(w_phrase)


    if len(noun_phrases) > 2 and not is_behoort:
        property_word = noun_phrases[0]
        entity_word = noun_phrases[1]
        value_word = noun_phrases[-1]
    elif len(noun_phrases) == 2 or is_behoort:
        entity_word = noun_phrases[0]
        value_word = noun_phrases[1]
    else:
        # if not, choose the last word of the sentence as the value
        value_word = parse[-1].lemma_
        if value_word == 'plant':
            value_word = 'planten'
        entity_word = noun_phrases[0].split()[0]

    #print(noun_phrases)
    # print('ent', entity_word, 'prop', property_word, 'val', value_word)

    return entity_word, property_word, value_word


def value_unit(phrase):

    '''
    Takes an input phrase and converts the 
    unit measurements to the wentity_word, property_word, value_wordikidata output format,
    then returns the new phrase as a string
    '''

    change_dict = {
        'jaren' : 'jaar',
        'maanden' : 'maand',
        'weken' : 'week',
        'dagen' : 'dag',
        'uren' : 'uur',
        'minuten' : 'minuut',
        'seconden' : 'seconde'
    }

    phrase_list = phrase.split()
    new_phrase = []
    value_num = phrase_list[0].replace('.','').replace(',','').isdigit() # check if value contains numbers
    for word in phrase_list:
        if word in change_dict.keys():
            new_phrase.append(change_dict[word])
        else:
            new_phrase.append(word)

    return ' '.join(new_phrase), value_num


def wikidata_value_formatize(phrase):

    '''
    Takes a wikidata value with unit measurements,
    checks if it contains unknown unit notations,
    removes them and returns a new value as a string
    '''
    phrase_list = phrase.split()

    if phrase_list[1] == "1" or phrase_list[1].startswith("Q"):
        return phrase_list[0]
    else:
        return ' '.join(phrase_list)


def run_query(ID1, ID2, hoeveel=False, ent_2='', prop_2=''):

    '''
    Takes two wikidata IDs and puts them in different
    queries, then returns the output of the query
    if the match was found as a list
    '''
    output = []
    amt = 0
    query = '''SELECT ?value ?unitLabel WHERE {wd:''' + ID2 + ''' p:''' + ID1 + ''' ?answer .
                            ?answer psv:''' + ID1 + ''' ?answernode .
                            ?answernode wikibase:quantityAmount ?value .
                            ?answernode wikibase:quantityUnit ?unit .
                            SERVICE wikibase:label { bd:serviceParam wikibase:language "nl" .}}
                            '''

    query2 = 'SELECT ?answerLabel WHERE { wd:' + ID2 + ' wdt:' + ID1 + ' ?answer . SERVICE wikibase:label { bd:serviceParam wikibase:language "nl" .}}'

    # Query 3 is added for the questions about how many sorts of animals there are of one specific animal (think of all sorts of cats.)
    query3 = 'SELECT ?answerLabel WHERE { ?answer wdt:' + ID1 + ' wd:' + ID2 + '. SERVICE wikibase:label { bd:serviceParam wikibase:language "nl" .}}'
    if prop_2 != '':
        query = 'SELECT ?value ?unitLabel WHERE { wd:' + ID2 + ' p:' + ID1 + ' ?answer . ?answer pq:' + prop_2 + ' wd:' + ent_2 + '. ?answer psv:' + ID1 + ' ?answernode .?answernode wikibase:quantityAmount ?value ; wikibase:quantityUnit ?unit. SERVICE wikibase:label { bd:serviceParam wikibase:language "nl" .}}'
        data = requests.get('https://query.wikidata.org/sparql', params={'query': query, 'format': 'json'}).json()
        try:
            if data["results"]["bindings"] != []:
                for item in data["results"]["bindings"]:
                    for var in item:
                        amt += 1
                        output.append("{}\t{}".format(var, item[var]["value"]))
        except:
            return "null"

    else:
        query_list = [query, query2, query3]

        try:
            for query in query_list:
                data = requests.get('https://query.wikidata.org/sparql', params={'query': query, 'format': 'json'}).json()
                if data["results"]["bindings"] != []:
                    for item in data["results"]["bindings"]:
                        for var in item:
                            amt+=1
                            output.append("{}\t{}".format(var,item[var]["value"]))
        except:
            return "null"

    if hoeveel:
        output = amt
    elif output == []: # to avoid exceeding the limits of queries per second
        sleep(5)
    return output


def run_desc_query(ID2):

    '''
    Recieves a wikidata entity ID to run
    an entity description query, then returns the
    results as a json file
    '''

    query_desc = '''SELECT ?entDesc WHERE 
                            {
                                SERVICE wikibase:label {
                                    bd:serviceParam wikibase:language "nl" .
                                    wd:''' + ID2 + ''' schema:description ?entDesc .
                                }
                            }
                        '''

    return requests.get('https://query.wikidata.org/sparql', params={'query': query_desc, 'format': 'json'}).json()


def get_id(word, word_type):

    '''
    Receives word and word type as strrings,
    finds their equivalents in wikidata database
    and returns list of matches as a dict
    '''

    url = 'https://www.wikidata.org/w/api.php'
    params = {'action':'wbsearchentities',
              'language':'nl',
              'uselang': 'nl',
              'format': 'json'}

    if word_type == 'property':
        params['type'] = 'property'

    params['search'] = word
    json = requests.get(url, params).json()

    return json['search']


def main():
    nlp = spacy.load("nl_core_news_lg")

    with open('test_questions.json') as f:
        questions = json.load(f)

    # question = input("Stel een vraag over een dier. \n")

    # question = "Waar is een hond goed voor?"
    # question = "Waar komt de kiwi voor?"
    # question = "Waar komen koala's voor?"
    # question = "Waar komen goudhamsters oorspronkelijk vandaan?"
    # question = "Waar komen de kiwi's vandaan?"
    # question = "Waar leven kiwi's?"
    # question = "Waar leeft de kangeroe?"
    # question = "Waar is de kiwi te vinden?"

    # question = "Welke kleur heeft een olifant?"
    # question = "Welke kleuren heeft de orca?"

    # question = "Wat is het unicode-symbool van een reuzenpanda?"
    # question = "Wat is de wetenschappelijke naam van de blobvis?"
    # question = "Wat is de hoogst geobserveerde levensduur van een zeehond?"
    # question = "Wat is de beschrijving van een pinguin?"
    # question = "Wat is de belangrijkste voedselbron van een tijger?"
    # question = "Wat eet een tijger?"

    # --- JA / NEE questions ---

    # question = "Behoren de olifanten tot de subklasse van zoogdieren?"
    # question = "Behoort de pinguin tot de familie van vogels?"
    # question = "Is de draagtijd van een kat 64 dagen?"
    # question = "Is de egel een bedreigde diersoort"
    # question = "Is de levensverwachting van een kat 14 jaar?" # Answer is no
    # question = "Is een olifant grijs?" # Does not work with multiple colors
    # question = "Zijn vleermuizen zoogdieren?"
    # question = "Zijn vleermuizen dieren?" # Answer is no
    # question = "Zijn vleermuizen 1.8288036 meter lang?"
    # question = "Eten olifanten planten?"
    # question = "Eet de koala bladeren?"
    # question = "Heeft de geit hoorns?" # Does not work :(
    # question = "Hebben geiten hoorns?"


    # ---- HOE / HOEVEEL questions ---
    # question = "Hoeveel soorten leeuwen zijn er?"
    # question = "Hoeveel weegt een tijger?"
    # question = "Hoe groot is een olifant?"
    # question = "Hoeveel eitjes legt een gewone octopus per keer?"
    # question = "Hoeveel eieren leggen reuzentoekans per keer?"
    # question = "Hoeveel weegt een tijger?"
    # question = "Hoeveel weegt een reuzenpanda?"
    # question = "Hoe zwaar is een ijsbeer?"
    # question = "Hoe groot is een olifant?"
    # question = "Hoe lang leeft een kat?"
    # question = "Hoeveel kinderen heeft een reuzentoekan per keer?"
    # question = "Hoeveel soorten leeuwen zijn er?"
    # question = "Hoeveel afbeeldingen van leeuwen zijn er?"
    # question = "Hoe lang is een wolf zwanger?"
    # question = "Hoe lang is de giraffe zwanger?" # TODO: Kijken of we ervoor kunnen zorgen dat 'lang' hier niet word gezien als de adjective.

    # question = "Hoe heet een goudvis in het Duits?"


    # ---- Questions about sorts of animals ----
    # question = "Kan je me een lijst geven van alle berensoorten?"
    # question = "Wat zijn alle soorten leeuwen?"
    # question = "Wat zijn alle soorten katten?"

    answer_list = []
    for q in questions:
        question = q['question']
        question = question.replace('elke kleuren', 'elke kleur')
        question = question.replace('?', '')
        parse = nlp(question)

        property_word = ""
        entity_word = ""
        value_word = ""
        hoeveel = False
        ent_2 = ''
        prop_2 = ''
        output = "Answer is not found"

        if str(parse[0]) == 'Hoe' or str(parse[0]) == 'Hoeveel':
            entity_word, property_word, hoeveel = hoe_questions(parse)
            entity_word = word_change(str(entity_word))
            property_word = word_change(str(property_word))

        elif str(parse[0]) == 'Welke':
            entity_word, property_word = welke_questions(parse)
            property_word = word_change(str(property_word))

        elif str(parse[0]) == 'Waar':
            entity_word, property_word = waar_questions(parse)
            property_word = word_change(property_word, True)
            entity_word = word_change(entity_word)

        elif str(parse[0]) == 'Zijn' or str(parse[0]) == 'Is':
            entity_word, property_word, value_word = janee_questions(parse, False)

        elif str(parse[0]) == 'Behoort'or str(parse[0]) == 'Behoren':
            entity_word, property_word, value_word = janee_questions(parse, True)

        # elif parse[0].pos_ == 'VERB' or parse[0].pos_ == 'AUX':
        #     entity_word, property_word, value_word = janee_questions(parse, False, parse[0].lemma_)

        else:
            all_chunks = []

            # Added a lemmatization for the chunk.root, so these words also get lemmatized.
            for word in parse:
                if word.pos_ == "VERB" and (word.text == "eet" or word.text == "eten"):
                    all_chunks.append(phrase(word)) 
                if word.pos_ == "NOUN":
                    all_chunks.append(phrase(word))
            if len(all_chunks[0]) == 1:
                property_word = re.sub(r'\bde\b|\bhet\b|\been\b', '', all_chunks[0])
            else:
                property_word = re.sub(r'\bde\b|\bhet\b|\been\b', '', all_chunks[0][0])
                ent_2 = get_id(all_chunks[0][1], 'entity')[0]['id']
                prop_2 = get_id(all_chunks[0][2], 'property')[0]['id']
            if len(all_chunks[1]) == 1:
                entity_word = re.sub(r'\bde\b|\bhet\b|\been\b', '', all_chunks[-1])
            else:
                entity_word = re.sub(r'\bde\b|\bhet\b|\been\b', '', all_chunks[-1][0])
                ent_2 = get_id(all_chunks[-1][1], "entity")[0]['id']
                prop_2 = get_id(all_chunks[-1][2], "property")[0]['id']

            # for the questions "Eet de koala bladeren"
            if parse[0].lemma_ == "eten":
                entity_word, property_word, value_word = janee_questions(parse, False, parse[0].lemma_)
                property_word = word_change(parse[0].lemma_)

            # entity_word = word_change(entity_word)
            entity_word = word_change(nlp(entity_word)[0].lemma_)

        # This is a check if 'soort' or what SpaCY thinks is the lemmatization of 'soorten'; 'soorat'.
        # If these two are in the entity word, that means that the entity word is a culmination like 'berensoorten'.
        if "soorten" in entity_word:
            entity_word = entity_word.replace("soorten", "")
            entity_word = nlp(entity_word)[0].lemma_
            id2_list = get_id(entity_word, "entity")

            property_word = "soort"
        
        elif "soort" in entity_word:
            entity_word = entity_word.replace("soorten", "")
            entity_word = nlp(entity_word)[0].lemma_
            id2_list = get_id(entity_word, "entity")

            property_word = "soort"
        
        elif "soorat" in entity_word:
            entity_word = entity_word.replace("soorat", "")
            entity_word = nlp(entity_word)[0].lemma_
            id2_list = get_id(entity_word, "entity")

            property_word = "soort"

        else:
            id2_list = get_id(entity_word, "entity")

        # process the queries that require property words
        # print(entity_word, property_word, value_word)
        if len(value_word) == 0:
            for i in range(len(id2_list)):
                output = []
                ID2 = id2_list[i]['id']

                if "beschrijving" in property_word:
                    data = run_desc_query(ID2)
                    if data["results"]["bindings"] != [{}]:
                        output = data["results"]["bindings"][0]["entDesc"]["value"]
                        break

                else:
                    if type(property_word) == list:
                        for word in property_word:
                            word = word_change(word)
                            ID1 = get_id(word, "property")[0]['id']
                            output = run_query(ID1, ID2, hoeveel, ent_2, prop_2)

                            if len(output) != 0:
                                break
                    else:
                        property_word = word_change(property_word.strip())
                        ID1 = get_id(property_word, "property")[0]['id']
                        output = run_query(ID1, ID2, hoeveel, ent_2, prop_2)


                    if isinstance(output, int) and output != 0:
                        break
                    if not isinstance(output, int) and len(output) != 0:
                        break

        # process the queries that require the value words (ja/nee questions)
        else:
            # change the format of the value word
            value_word, is_value_num = value_unit(value_word)

            # Loop through the first 3 possible entries of the entity
            output = "No"
            for i in range(len(id2_list[:3])):

                ID2 = id2_list[i]['id']

                query_unit = '''SELECT ?wdLabel ?final WHERE {
                            {
                                SELECT DISTINCT ?wdLabel ?unitLabel ?value WHERE
                                {
                                    wd:''' + ID2 + ''' ?p ?statement .
                                    ?statement ?ps ?ps_ .
                                    ?ps_ wikibase:quantityAmount ?value ;
                                        wikibase:quantityUnit ?unit .

                                    
                                    ?wd wikibase:claim ?p;
                                        rdf:type wikibase:Property.
                                    
                                    SERVICE wikibase:label {bd:serviceParam wikibase:language "nl" }
                                }
                            }
                            BIND(concat(STR(?value)," ",STR(?unitLabel)) AS ?final)
                            }
                        '''
                

                query_text = '''SELECT DISTINCT ?propUrl ?propLabel ?valUrl ?valLabel  WHERE
                                {
                                    wd:''' + ID2 + ''' ?propUrl ?valUrl.
                                    ?property ?ref ?propUrl;
                                                rdf:type wikibase:Property;
                                                rdfs:label ?propLabel.
                                    ?valUrl rdfs:label ?valLabel.
                                    FILTER((LANG(?propLabel)) = "nl")
                                    FILTER((LANG(?valLabel)) = "nl")
                                }
                                ORDER BY (?propUrl) (?valUrl)'''

                data = requests.get('https://query.wikidata.org/sparql', params={'query': query_unit, 'format': 'json'}).json()


                # run the query with only numerical values as outputs
                if is_value_num:
                    for item in data["results"]["bindings"]:
                        wiki_value = wikidata_value_formatize(item["final"]["value"])
                        if value_word == wiki_value:
                            # extra validation of the property value if exists in the question
                            if property_word != "":
                                if item["wdLabel"]["value"] in property_word:
                                    output = "Yes"
                            # if no property value is mentioned in the question
                            else:
                                output = "Yes"

                else:
                    # run the query that checks the entity description only
                    data = run_desc_query(ID2)
                    if data["results"]["bindings"] != [{}]:
                        if data["results"]["bindings"][0]["entDesc"]["value"] in value_word:
                            output = "Yes"

                        else:
                            # run the query that prints all entity's properties and values
                            data = requests.get('https://query.wikidata.org/sparql', params={'query': query_text, 'format': 'json'}).json()
                            for item in data["results"]["bindings"]:
                                # print(item["propLabel"]["value"], item["valLabel"]["value"])
                                # find a match between the value in the question and value in the output
                                if item["valLabel"]["value"] in value_word and item["valLabel"]["value"] != "soort":

                                    # extra validation of the property value if exists in the question
                                    if property_word != "":
                                        if item["propLabel"]["value"] in property_word:
                                            output = "Yes"

                                    # else assume no property exists in the question
                                    else:
                                        output = "Yes"


                if output == "Yes":
                    break

        if type(output) is list:
            for i in output:
                print(i)

            output = ", ".join(output)
            output = output.replace("answerLabel\t", "")
            answer_dict = {
                "id" :  q['id'],
                "question" : q['question'],
                "answer" : output,
                "correct" : 0
            }

            answer_list.append(answer_dict)
        else:
            answer_dict = {
                "id" :  q['id'],
                "question" : q['question'],
                "answer" : output,
                "correct" : 0
            }
            answer_list.append(answer_dict)

            print(output)
        # Sleep because otherwise Wikidata gets overused
        sleep(5)
    
    with open("system.json", "w") as outfile:
        json.dump(answer_list, outfile)

        

if __name__ == "__main__":
   main()