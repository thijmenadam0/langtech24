#
#
#
#

import requests
import re
import spacy


def phrase(word):
    children = []
    for child in word.subtree :
        children.append(child.text)
    result = " ".join(children)
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
            #entity_word = word.lemma_
            entity_word = phrase(word)
        elif word.dep_ == 'obj':
            property_word = word.lemma_

    return entity_word, property_word


def hoe_questions(parse):
    '''This function makes it so it returns the entity and property
    words for questions sarting with 'hoe'
    '''
    for word in parse:
        if word.pos_ == 'NOUN':
            #entity_word = word.lemma_
            entity_word = phrase(word)

        elif word.dep_ == "ROOT" and (word.pos_ == 'ADJ' or word.pos_ == 'VERB'):
            property_word = word.lemma_
    
    return entity_word, property_word


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
    question = "Wat is de spanwijdte van de blauwe reiger?"
    # question = "Hoe zwaar is een ijsbeer?"
    question = question.replace("elke kleuren", "elke kleur")
    parse = nlp(question)

    if str(parse[0]) == 'Hoe' or str(parse[0]) == 'Hoeveel':
        entity_word, property_word = hoe_questions(parse)
        property_word = word_change(str(property_word))

    elif str(parse[0]) == 'Welke':
        entity_word, property_word = welke_questions(parse)
        property_word = word_change(str(property_word))


    else:
        all_chunks = []
        for chunk in parse.noun_chunks:
            all_chunks.append(chunk.text)
        property_word = re.sub(r'\bde\b|\bhet\b|\been\b', '', all_chunks[0])
        entity_word = re.sub(r'\bde\b|\bhet\b|\been\b', '', all_chunks[1])

    ID1 = get_id(property_word, "property")[0]['id']
    id2_list = get_id(entity_word, "entity")

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

    for i in output:
        print(i)

        

if __name__ == "__main__":
   main()