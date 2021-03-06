#!/usr/bin/env python
'''
Created on May 14, 2014
@author: reid

Modified on May 21, 2015
'''
import chunk
import qa
import nltk, operator
import spacy,re
from rake_nltk import Rake
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.corpus import wordnet as wn
import wordnet_demo
LMTZR = WordNetLemmatizer()
nlp = spacy.load('en_core_web_lg')

# The standard NLTK pipeline for POS tagging a document
def get_sentences(text):
    sentences = nltk.sent_tokenize(text)
    sentences = [nltk.word_tokenize(sent) for sent in sentences]
    sentences = [nltk.pos_tag(sent) for sent in sentences]
    
    return sentences	

def get_bow(tagged_tokens, stopwords):
    return set([t[0].lower() for t in tagged_tokens if t[0].lower() not in stopwords])

def find_phrase(tagged_tokens, qbow):
    for i in range(len(tagged_tokens) - 1, 0, -1):
        word = (tagged_tokens[i])[0]
        if word in qbow:
            return tagged_tokens[i+1:]

def expand_rake(raked_phrases):
    all_words = set()
    for phrases in raked_phrases:
        for words in nltk.word_tokenize(phrases):
            all_words.add(words)
    return all_words

def get_array_of_sets(the_rake,sid, noun_ids, verb_ids):
    the_total = 0
    listofsets = []
    for word in the_rake:
        synset_sets = set()
        word_net_list = []
        word_net_list.extend(wn.synsets(word))
        for mini_word in wn.synsets(word):
            word_net_list.extend(mini_word.hyponyms())
            word_net_list.extend(mini_word.hypernyms())

        for mini_word in word_net_list:
            if wordnet_demo.wordincsv(mini_word.name()[0:mini_word.name().index(".")],sid, noun_ids, verb_ids):
                synset_sets.add(mini_word.name()[0:mini_word.name().index(".")])
        listofsets.append(synset_sets)
        #if len(list(synset_sets & sbow)) > 0:
        #    the_total += 3 #tbd ( I think it works better the larger it is)

    return listofsets

def get_candidate(min_index, sent_index, sentences, tags, gender): #scan sents in order of recency for candidates
    candidates = {}
    for i in reversed(range(min_index, sent_index)):
        sent = sentences[i]
        for word, tag in sent:
            if tag in tags and match_gender(word, gender): #Assign scores with recency decay
                if word in candidates: candidates[word] = candidates[word] + sent_index-min_index-i
                else: candidates[word] = 10 - (sent_index - min_index - i)*2
    if not bool(candidates): return None
    #Getting highest ranked item
    max_score = 0
    output = None
    for item, score in candidates.items(): 
        if score > max_score:
            max_score = score
            output = item
    #print(" ".join(word[0] for word in sentences[sent_index]))
    #print(output)
    return output

def match_gender(word, gender):
    if gender in ['obj','group']: return True
    if (word[0] < 'A' or word[0] > 'Z'): return False
    return True

MALE_PRONOUNS=set(["he","him"])
FEMALE_PRONOUNS=set(["she","her"])
OBJECT_PRONOUNS=set(["it"])
GROUP_PRONOUNS=set(["they"])
def sub_proper_nouns(sentences, n=2):
    #if (n == 2): return sentences
    for i in range(0, len(sentences)):
        sent = sentences[i]
        minimum = max(i-n,0)
        j = 0
        word = sent[j][0]
        tag = sent[j][1]
        if word in MALE_PRONOUNS: candidate = get_candidate(minimum, i, sentences, ["NNP","NN"], "male")
        elif word in FEMALE_PRONOUNS: candidate = get_candidate(minimum, i, sentences, ["NNP","NN"], "female")
        elif word in OBJECT_PRONOUNS: candidate = get_candidate(minimum, i, sentences, ["NN", "NNP"], "obj")
        elif word in GROUP_PRONOUNS: candidate = get_candidate(minimum, i, sentences, ["NNS","NNPS"], "group")
        else: candidate = None
        sentences[i][j] = (candidate if candidate != None else word, tag)
        #if candidate != None: print(" ".join(word[0] for word in sentences[i]))
    return sentences

def get_overlap(sbow, setofsets):
    total = 0
    for the_set in setofsets:
        
        for item in the_set:
            if len(list(sbow&set([item]))) > 0:
                total += 3
                break
    return total
def baseline(qbow, sentences, stopwords,question, raked_phrases,sid, noun_ids, verb_ids):
    # Collect all the candidate answers
    raked_phrases_list = expand_rake(raked_phrases)
    sentences = sub_proper_nouns(sentences)
    answers = []
    number = 0

    temp = []
    pos_rake=nltk.pos_tag(raked_phrases_list)
    for word,tag in pos_rake:
        if re.search("VB", tag):
            temp.append((LMTZR.lemmatize(word, "v")))
        elif re.search("NN",tag):
            temp.append((LMTZR.lemmatize(word,"n")))
        else:
            temp.append(word)
    the_rake = set(temp)

    setofsets = get_array_of_sets(the_rake,sid, noun_ids, verb_ids)
    for sent in sentences:
        # A list of all the word tokens in the sentence
        sbow = get_bow(sent, stopwords)
        #print(qbow)
        pos_sbow=nltk.pos_tag(sbow)

        temp=[]
        for word,tag in pos_sbow:
            ###
            if re.search("VB", tag):
                temp.append((LMTZR.lemmatize(word, "v")))
            elif re.search("NN",tag):
                temp.append((LMTZR.lemmatize(word,"n")))
            else:
                temp.append(word)
        
        sbow=set(temp)

        pos_qbow=nltk.pos_tag(qbow)
        temp=[]
        for word,tag in pos_qbow:
            if re.search("VB", tag):
                temp.append((LMTZR.lemmatize(word, "v")))
            elif re.search("NN",tag):
                temp.append((LMTZR.lemmatize(word,"n")))
            else:
                temp.append(word)
        qbow=set(temp)

        

        #print(sbow)
        # Count the # of overlapping words between the Q and the A
        # & is the set intersection operator
        #overlap = len(qbow & sbow)
        testoverlap=0
        testoverlap += get_overlap(sbow,setofsets)
        overlapp= list(qbow & sbow)
        overlapp= nltk.pos_tag(overlapp)
        for word,tag in overlapp:
            if re.search("N", tag):
                testoverlap+=2
            if re.search("V",tag):
                testoverlap+=2
            else:
                testoverlap+=1
        
        answers.append((testoverlap, sent, number))
        number += 1
    # Sort the results by the first element of the tuple (i.e., the count)
    # Sort answers from smallest to largest by default, so reverse it
    answers = sorted(answers, key=operator.itemgetter(0), reverse=True)

    #for sent in best_candidate_sents: #Filter using Rake
    #    ans_tagged = set([word[0] for word in sent])
    #    best_overlap = len(ans_tagged & qbow)
    #    candidates_ranked_on_rake.append((ans_tagged, best_overlap))
    #print(candidates_ranked_on_rake)
    #best_answer = sorted(candidates_ranked_on_rake, key=takeSecond)

    # Return the best answer
    top_answers=[]
    max_overlap=(answers[0])[0]
    for answer in answers:
        if answer[0]==max_overlap:
            top_answers.append(answer)
    similarity=0
    best_answer=""
    question=nltk.word_tokenize(question)
    question[0]=""
    length=len(question)-1
    question[length]=""
    stopwords = set(nltk.corpus.stopwords.words("english"))
    stopwords.add('was')
    question = " ".join(word for word in question if word not in stopwords)
    question=nlp(question)
    #print(top_answers)
    if(len(top_answers)>1):
        #print("in here")
        #print(top_answers[0])
        for answer in top_answers:
           
            sentence= " ".join(t[0] for t in answer[1])
            temp_sim=question.similarity(nlp(sentence))
            if temp_sim>similarity:
                best_answer=answer[1]
                index=answer[2]
                similarity=temp_sim
            
            #print("sentence:", " ".join(t[0] for t in answer)," ",temp_sim)
        return best_answer,index


    best_answer = (answers[0])[1]    
    index = (answers[0])[2]
    return best_answer, index


if __name__ == '__main__':

    question_id = "fables-01-1"

    driver = QABase()
    q = driver.get_question(question_id)
    story = driver.get_story(q["sid"])
    text = story["text"]
    question = q["text"]
    print("question:", question)
    stopwords = set(nltk.corpus.stopwords.words("english"))

    qbow = get_bow(get_sentences(question)[0], stopwords)
    #print(find_phrase(get_sentences(question)[0],qbow))
    sentences = get_sentences(text)
    answer = baseline(qbow, sentences, stopwords)
    print("answer:", " ".join(t[0] for t in answer))
