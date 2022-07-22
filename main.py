import requests
import anki.collection as collection
import anki
import json
import re
import time
from kana import kanas

headers = {'accept': 'application/json'}
TagDict = {
        'Noun' : 'noun',
        'Suru verb' : 'verb::suru',
        'Godan verb' : 'verb::godan',
        'Ichidan verb' : 'verb::ichidan',
        'Na-adjective' : 'adjective::na',
        'I-adjective' : 'adjective::i',
        'fukushi' : 'adverb::fukushi',
        "Adverb taking the 'to' particle" : 'adverb::to',
        'Expressions' : 'expression',
        "Noun which may take the genitive case particle 'no'" : 'noun::no',
        'Noun, used as a suffix' : 'noun::suffix',
        'Prefix' : 'prefix',
        'Suffix' : 'suffix'
        }

JishoCount = 0

def JishoLookup(Kanji):
    JishoResponse = []
    global JishoCount
    for n in range(5):
        # for now this only scrapes jisho-responses
        # which are marked with jlpt-n5 to jlpt-n1 levels
        url = 'https://jisho.org/api/v1/search/words?keyword=*' + Kanji + '*%20%23jlpt-n' + str(5-n)
        response = requests.get(url, headers = headers)
        JishoResponse += json.loads(response.text)['data']
        JishoCount += 1
        if JishoCount%40 == 0:
            print('sleep :3')
            time.sleep(5)

    return JishoResponse

def CreateFurigana(JishoEntry):
    # Very crude way of adding furiganas to kanjis

    word = JishoEntry['japanese'][0]['word']
    reading = JishoEntry['japanese'][0]['reading']

    Kanjis = ''.join([n for n in word if n not in kanas])
    idx = [word.index(Kanji) for Kanji in Kanjis]

    if Kanjis == word:
        # This splits the full reading returned by jisho into
        # chunks of equal lenght and adds such a chunk to each
        # kanji.
        # Sometimes this works but most of the time it doesn't.
        # Be prepared to double check the output
        parts = len(word)
        readinglen = len(reading)
        partlen = -(-readinglen//parts)
        furigana = [reading[n*partlen:min([readinglen, n*partlen + partlen])] for n in range(parts)]
        furigana = ''.join([''.join([x, '[',  y, ']']) for x, y in zip(list(word), furigana)])

    elif len(idx) == max(idx)+1:
        # This does the same as above,
        # except it cuts of the kana tail
        idx = max(idx) - len(word) + 1
        parts = len(word[:idx])
        readinglen = len(reading[:idx])
        partlen = -(-readinglen//parts)
        furiganas = [reading[n*partlen:min([readinglen, n*partlen + partlen])] for n in range(parts)]
        furigana = ''.join([''.join([x, '[', y, ']']) for x, y in zip(list(word[:idx]), furiganas)] + [word[idx:]])

    else:
        # This is a truly borked way of adding furigana to words.
        # Expect this to give very weird results.
        try:
            tmpfurigana = []
            tmpreading = ''.join([n for n in reading if n not in list(word)])
            parts = len(Kanjis)
            readinglen = len(tmpreading)
            partlen = -(-readinglen//parts)
            furiganas = [tmpreading[n*partlen:min([readinglen, n*partlen + partlen])] for n in range(parts)]
            furigana = {Kanji : '[' + furigana + ']' for Kanji, furigana in zip(Kanjis, furiganas)}
            for n in word:
                if n not in kanas:
                    tmpfurigana.append(''.join([' ', n, furigana[n]]))
                else:
                    tmpfurigana.append(n)
            if tmpfurigana[0][0] == ' ':
                tmpfurigana[0] = tmpfurigana[0][1:]

            furigana = ''.join(tmpfurigana)
        except:
            furigana = word + '[' + reading + ']'

    return furigana

def CreateCard(JishoEntry):
    # This will take an entry of Jishos API response and turn it into
    # a string which can be read by Anki.
    # Currently this supports Standard words, Prefixes, Suffixes
    # and Words which are usually written with kanas alone.
    Tags = []
    Kanjis = [Char for Char in JishoEntry['japanese'][0]['word'] if Char not in kanas]

    jlpt = [lvl[-1] for lvl in JishoEntry['jlpt']]
    Tags.append('jlpt::n' + str(max(jlpt)))
    for partofspeech in JishoEntry['senses'][0]['parts_of_speech']:
        for tag in list(TagDict.keys()):
            if re.search(tag, partofspeech):
                Tags.append(TagDict[tag])

    Tags += ['漢字::' + Char for Char in JishoEntry['japanese'][0]['word'] if Char not in kanas]

    suffix = ''
    prefix = ''

    if 'suffix' in Tags:
        suffix = '~ '

    if 'prefix' in Tags:
        prefix = ' ~'

    for tag in JishoEntry['senses'][0]['tags']:
        if re.search(tag, 'Usually written using kana alone'):
            Card = '(usually written using kana alone) ' + '\t'.join([
                suffix + JishoEntry['japanese'][0]['word'] + prefix,
                suffix + JishoEntry['japanese'][0]['reading'] + prefix,
                ', '.join(JishoEntry['senses'][0]['english_definitions'])
                ] + [' '.join(Tags)])
            return Card, Kanjis

    furigana = CreateFurigana(JishoEntry)

    Card = '\t'.join([
        suffix + JishoEntry['japanese'][0]['word'] + prefix,
        suffix + furigana + prefix,
        ', '.join(JishoEntry['senses'][0]['english_definitions'])
        ] + [' '.join(Tags)])

    return Card, Kanjis

def CreateCards(AllKanjis, LearnedKanjis, n = 1, offset = 0):
    # This Function takes a list of 'All' kanjis and a 
    # list of all learned kanjis as inputs. It will then
    # create cards with the info given by Jishos API response
    # for the next n kanjis in the list of AllKanjis.
    # This will only append new cards if all Kanjis in the
    # new word appear in LearnedKanjis.
    Cards = ''
    try:
        LearnedIndex = AllKanjis.index(LearnedKanjis[-1])
    except:
        LearnedIndex = -1

    OffsetKanjis, NewKanjis = AllKanjis[LearnedIndex+1:LearnedIndex+1+offset], AllKanjis[LearnedIndex+1+offset:]
    LearnedKanjis += OffsetKanjis

    for i in range(n):
        JishoResponse = JishoLookup(NewKanjis[i])
        LearnedKanjis.append(NewKanjis[i])

        for word in JishoResponse:
            try:
                Card, Kanjis = CreateCard(word)
            except:
                pass

            if all(elem in ['々'] + LearnedKanjis for elem in Kanjis):
                Cards = '\n'.join([Cards, Card])

    return Cards[1:]

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
    Cards = CreateCards(AllKanjis, [], n = 1, offset = 289)
    file = open('newcards', 'w', encoding='utf-8')
    file.write(Cards)
    file.close()

if __name__ == '__main__':
    main()
