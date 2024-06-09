#
#
#
#

import requests
import re
import spacy


def phrase(word):
    '''
    This function takes a noun, collects the corresponding
    to the noun children in the sentence, combines them in
    a noun phrase and returns as a string
    '''
    children = []
    for child in word.subtree :
        if child.dep_ != 'cop' and child.dep_ != 'nmod:poss': # get rid of words 'zijn' and 'is'
            if word.dep_ == "ROOT":
                # allow only adj and det to be added to the root noun phrase
                if child.pos_ == "ADJ" or child.pos_ == "DET" or child.dep_ == "amod": # amod for 'bedreigde diersoort'
                    children.append(child.text)
                elif child.text == word.text:
                    children.append(child.lemma_)
            else:
                children.append(child.text)
    result = " ".join(children)
    result = re.sub(r'^(van |tot )', '', result) # remove cases of noun phrases like 'van een kat' 'tot de familie...'
    return re.sub(r'^(de |het |een )', '', result)


def word_change(word):
    '''Changes a word to a word that wikidata understand'''

    prop_words = {
        'groot': 'hoogte',
        'hoog': 'hoogte',
        'lang': 'hoogte',
        'oud': 'levensverwachting',
        'leven': 'levensverwachting',
        'zwaar': 'gewicht',
        'wegen': 'gewicht',
        'heten': 'naam'
    }

    verb_words = {
        'hebben' : 'omvat deel',
        'eten' : ''
    }

    if word in prop_words:
        return prop_words[word]
    
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


def hoe_questions(parse):
    '''This function makes it so it returns the entity and property
    words for questions sarting with 'hoe'
    '''
    for word in parse:
        if word.pos_ == 'NOUN' and word.dep_ == 'nsubj': # TODO: find out why I added word.dep_ in the first place
            #entity_word = word.lemma_
            entity_word = phrase(word)

        elif word.dep_ == "ROOT" and (word.pos_ == 'ADJ' or word.pos_ == 'VERB'):
            property_word = word.lemma_
    
    return entity_word, property_word


def janee_questions(parse, is_behoort):

    '''
    This function takes a sentence parse, takes the necessary
    noun phrases from it and assigns them to the variables,
    then returns them as strings
    '''

    property_word = ""
    noun_phrases = []
    for word in parse:
        # print(word, word.pos_, word.dep_)
        if word.pos_ == 'NOUN':
            noun_phrases.append(phrase(word))


    if len(noun_phrases) > 2 and not is_behoort:
        property_word = noun_phrases[0]
        entity_word = noun_phrases[1]
        value_word = noun_phrases[-1]
    elif len(noun_phrases) == 2 or is_behoort:
        entity_word = noun_phrases[0]
        value_word = noun_phrases[1]
    else:
        # if not, choose the last word of the sentence as the value
        value_word = parse[-2].lemma_ # [-1] is always punctuation
        entity_word = noun_phrases[0].split()[0]

    #print(noun_phrases)
    #print(entity_word, property_word, value_word)

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

    # question = input("Stel een vraag over een dier. \n")

    # question = "Welke kleur heeft een olifant?"
    # question = "Welke kleuren heeft een orca?"
    # question = "Hoeveel weegt een tijger?"
    # question = "Hoeveel weegt een reuzenpanda?"
    # question = "Hoe zwaar is een ijsbeer?"
    # question = "Hoe groot is een olifant?"
    # question = "Hoe lang leeft een kat?"

    # question = "Wat is het unicode-symbool van een reuzenpanda?"
    # question = "Wat is de wetenschappelijke naam van de blobvis?"
    # question = "Wat is de hoogst geobserveerde levensduur van een zeehond?"

    # --- JA / NEE questions ---

    # question = "Behoren de olifanten tot de subklasse van zoogdieren?"
    question = "Behoort de pinguin tot de familie van vogels?"
    # question = "Is de draagtijd van een kat 64 dagen?"
    # question = "Is de levensverwachting van een kat 14 jaar?" # Answer is no
    # question = "Is een olifant grijs?" # Does not work with multiple colors
    # question = "Zijn vleermuizen zoogdieren?"
    # question = "Zijn vleermuizen dieren?" # Answer is no
    # question = "Zijn vleermuizen 1.8288036 meter lang?"

    question = question.replace('elke kleuren', 'elke kleur')
    question = question.replace('?', '')
    parse = nlp(question)

    property_word = ""
    entity_word = ""
    value_word = ""

    if str(parse[0]) == 'Hoe' or str(parse[0]) == 'Hoeveel':
        entity_word, property_word = hoe_questions(parse)
        property_word = word_change(str(property_word))

    elif str(parse[0]) == 'Welke':
        entity_word, property_word = welke_questions(parse)
        property_word = word_change(str(property_word))

    elif str(parse[0]) == 'Zijn' or str(parse[0]) == 'Is':
        entity_word, property_word, value_word = janee_questions(parse, False)

    elif str(parse[0]) == 'Behoort'or str(parse[0]) == 'Behoren':
        entity_word, property_word, value_word = janee_questions(parse, True)

    else:
        all_chunks = []
        for chunk in parse.noun_chunks:
            all_chunks.append(chunk.text)
        property_word = re.sub(r'\bde\b|\bhet\b|\been\b', '', all_chunks[0])
        entity_word = re.sub(r'\bde\b|\bhet\b|\been\b', '', all_chunks[1])

    id2_list = get_id(entity_word, "entity")

    # process the queries that require property words
    if len(value_word) == 0:
        ID1 = get_id(property_word, "property")[0]['id']

        for i in range(len(id2_list)):
            output = []
            ID2 = id2_list[i]['id']
            query = '''SELECT ?value ?unitLabel WHERE {wd:''' + ID2 + ''' p:''' + ID1 + ''' ?answer .
                    ?answer psv:''' + ID1 + ''' ?answernode .
                    ?answernode wikibase:quantityAmount ?value .
                    ?answernode wikibase:quantityUnit ?unit .
                    SERVICE wikibase:label { bd:serviceParam wikibase:language "nl" .}}
                    '''

            query2 = 'SELECT ?answerLabel WHERE { wd:' + ID2 + ' wdt:' + ID1 + ' ?answer . SERVICE wikibase:label { bd:serviceParam wikibase:language "nl" .}}'

            data = requests.get('https://query.wikidata.org/sparql', params={'query': query, 'format': 'json'}).json()

            if data["results"]["bindings"] != []:
                for item in data["results"]["bindings"]:
                    for var in item:
                        output.append("{}\t{}".format(var,item[var]["value"]))

            else:
                data = requests.get('https://query.wikidata.org/sparql', params={'query': query2, 'format': 'json'}).json()
                for item in data["results"]["bindings"]:
                    for var in item:
                        output.append("{}\t{}".format(var,item[var]["value"]))

            if len(output) != 0:
                break

    # process the queries that require the value words (ja/nee questions)
    else:
        # change the format of the value word
        value_word, is_value_num = value_unit(value_word)

        # Loop through the first 3 possible entries of the entity
        for i in range(len(id2_list[:3])):
            output = "No"
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
            
            query_desc = '''SELECT ?entDesc WHERE 
                            {
                                SERVICE wikibase:label {
                                    bd:serviceParam wikibase:language "nl" .
                                    wd:''' + ID2 + ''' schema:description ?entDesc .
                                }
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
                data = requests.get('https://query.wikidata.org/sparql', params={'query': query_desc, 'format': 'json'}).json()
                if data["results"]["bindings"] != [{}]:
                    if data["results"]["bindings"][0]["entDesc"]["value"] in value_word:
                        output = "Yes"

                    else:
                        # run the query that prints all entity's properties and values
                        data = requests.get('https://query.wikidata.org/sparql', params={'query': query_text, 'format': 'json'}).json()
                        for item in data["results"]["bindings"]:
                            # print(item["propLabel"]["value"], item["valLabel"]["value"])
                            # find a match between the value in the sentence and value in the output
                            if item["valLabel"]["value"] in value_word:
                                # extra validation of the property value if exists in the question
                                if property_word != "":
                                    if item["propLabel"]["value"] in property_word:
                                        output = "Yes"
                                else:
                                    output = "Yes"


            if output == "Yes":
                break

    if type(output) is list:
        for i in output:
            print(i)
    else:
        print(output)

        

if __name__ == "__main__":
   main()