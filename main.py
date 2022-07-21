import requests
import anki.collection as collection
import anki
import json
import re
from kana import kanas

headers = {'accept': 'application/json'}
TagDict = {
        'Noun' : 'noun',
        'Suru verb' : 'verb::suru',
        'Godan verb' : 'verb::godan',
        'Ichidan verb' : 'verb::ichidan',
        'Na-adjective' : 'adjective::na',
        'I-adjective' : 'adjective::i',
        'Adverb (fukushi)' : 'adverb::fukushi',
        "Adverb taking the 'to' particle" : 'adverb::to',
        'Expressions' : 'expression',
        "Noun which may take the genitive case particle 'no'" : 'noun::no',
        'Noun, used as a suffix' : 'noun:suffix',
        'Prefix' : 'prefix'
        }

def JishoLookup(Kanji):
    JishoResponse = []
    for n in range(3):
        url = 'https://jisho.org/api/v1/search/words?keyword=*' + Kanji + '*%20%23jlpt-n' + str(5-n)
        response = requests.get(url, headers = headers)
        JishoResponse += json.loads(response.text)['data']

    return JishoResponse

def PreciseJishoLookup(Kanji):
    JishoResponse = []
    for n in range(2):
        url = 'https://jisho.org/api/v1/search/words?keyword=*' + Kanji + '*%20%23jlpt-n' + str(2-n)
        response = requests.get(url, headers = headers)
        JishoResponse += json.loads(response.text)['data']

    return JishoResponse

def CreateCard(JishoEntry):
    Tags = []
    Kanjis = []

    jlpt = [str(lvl[-1]) for lvl in JishoEntry['jlpt']]
    Tags.append('jlpt::n' + str(max(jlpt)))
    for partofspeech in JishoEntry['senses'][0]['parts_of_speech']:
        for tag in list(TagDict.keys()):
            if re.match(tag, partofspeech):
                Tags.append(TagDict[tag])

    for Char in JishoEntry['japanese'][0]['word']:
        if Char not in kanas:
            Tags.append('漢字::' + Char)
            Kanjis.append(Char)

    Card = '\t'.join([JishoEntry['japanese'][0]['word'], JishoEntry['japanese'][0]['word'] + '['+ JishoEntry['japanese'][0]['reading'] + ']', ', '.join(JishoEntry['senses'][0]['english_definitions'])] + [' '.join(Tags)])
    return Card, Kanjis

def CreateCards(AllKanjis, LearnedKanjis, n = 1, offset = 0):
    Cards = ''
    LearnedIndex = AllKanjis.index(LearnedKanjis[-1])
    NewKanjis = AllKanjis[LearnedIndex+1:]
    for i in range(n):
        i += offset
        JishoResponse = JishoLookup(NewKanjis[i])
        LearnedKanjis.append(NewKanjis[i])
        if not JishoResponse:
            JishoResponse = PreciseJishoLookup(NewKanjis[i])

        for word in JishoResponse:
            Card, Kanjis = CreateCard(word)
            if all(elem in LearnedKanjis for elem in Kanjis):
                Cards += Card + '\n'

    return Cards

def main():
    col = collection.Collection('data/collection.anki2')
    KanjiDeckID = col.decks.all_names_and_ids()[-2].id
    KanjiDeckID = '(' + str(KanjiDeckID) + ')'
    KanjiExamplesDeckID = col.decks.all_names_and_ids()[-3].id
    AllKanjiIDs = col.db.all(
            f"""\
                    SELECT  nid
                    FROM    cards
                    WHERE   did IN {KanjiDeckID}
                                """)
    AllKanjiIDs = '(' + ', '.join(str(nid)[1:-1] for nid in AllKanjiIDs) + ')'
    AllKanjis = col.db.all(
            f"""\
                    SELECT  flds
                    FROM    notes
                    WHERE   id  IN {AllKanjiIDs}
                    """)
    AllKanjis = [re.sub('\x1f', ' ', Kanji[0]).split()[1] for Kanji in AllKanjis]
    LearnedKanjiIDs = col.db.all(
            f"""\
                    SELECT  nid
                    FROM    cards
                    WHERE   did IN {KanjiDeckID}
                                AND ivl > 0
                                """)
    LearnedKanjiIDs = '(' + ', '.join(str(nid)[1:-1] for nid in LearnedKanjiIDs) + ')'
    LearnedKanjis = col.db.all(
            f"""\
                    SELECT  flds
                    FROM    notes
                    WHERE   id  IN {LearnedKanjiIDs}
                    """)
    LearnedKanjis = [re.sub('\x1f', ' ', LearnedKanji[0]).split()[1] for LearnedKanji in LearnedKanjis]
    LearnedIndex = AllKanjis.index(LearnedKanjis[-1])
    Cards = CreateCards(AllKanjis, LearnedKanjis, n = 6, offset = 12)
    file = open('newcards', 'w')
    file.write(Cards)
    file.close()

if __name__ == '__main__':
    main()
