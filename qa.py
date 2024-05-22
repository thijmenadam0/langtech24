#
#
#
#

import requests
import re
import spacy


def word_change(word):
  '''Changes a word to a word that wikidata understand'''
  if "groot" in word or "hoog" in word or "lang" in word:
    return "hoogte"
  if "oud" in word:
    return "levensverwachting"
  if "zwaar" in word or "weegt" in word:
    return "gewicht"
  if "heet" in word:
    return "naam"
  if "leeft" in word:
    return "levensverwachting"
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
        entity_word = word
      elif word.dep_ == 'obj':
        property_word = word

    return entity_word, property_word


def hoe_questions(parse):
    '''This function makes it so it returns the entity and property
    words for questions sarting with 'hoe'
    '''
    for word in parse:
        if word.pos_ == 'NOUN':
            entity_word = word.text
        elif word.pos_ == 'ADJ' or word.pos_ == 'VERB':
            property_word = word.text
    return entity_word, property_word


def main():
    nlp = spacy.load("nl_core_news_lg")

    question = input("Stel een vraag over een dier. \n")
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

    url = 'https://www.wikidata.org/w/api.php'
    params = {'action':'wbsearchentities',
            'language':'nl',
            'uselang':'nl',
            'format':'json'}

    params_p = {'action':'wbsearchentities',
                'type':'property',
                'language':'nl',
                'uselang':'nl',
                'format':'json'}

    params_p['search'] = property_word
    params['search'] = str(entity_word)

    json = requests.get(url,params_p).json()
    ID1 = json['search'][0]['id']

    json = requests.get(url,params).json()
    ID2 = json['search'][0]['id']

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
                print("{}\t{}".format(var,item[var]["value"]))

    else:
        data = requests.get('https://query.wikidata.org/sparql', params={'query': query2, 'format': 'json'}).json()
        for item in data["results"]["bindings"]:
            for var in item:
                print("{}\t{}".format(var,item[var]["value"]))


if __name__ == "__main__":
   main()