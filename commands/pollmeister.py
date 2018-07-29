import string
import nltk
import time

from nltk import bigrams
from nltk.stem import *
from nltk.stem.snowball import SnowballStemmer
from threading import Thread

ONE_PER_USER = True
polls = []

stemmer = SnowballStemmer("english")

class Poll(object):
    def __init__(self, index, bot, channel, name, timeout):
        self.index = index
        self.channel = channel
        self.votes = []
        self.bot = bot
        self.name = name
        self.voted = set()
        self.time = time.time()
        self.timeout = timeout
        
        polls.append(self)
        
        if len([x for x in polls if x is not None]) < 2:
            self.message("Poll #{1} created! Vote on it with '{0}vote <vote>'. {2:.2f} seconds remaining!".format(bot.prefix, index, timeout))
        
        else:
            self.message("Poll #{1} created! Vote on it with '{0}vote {1} <vote>'. {2:.2f} seconds remaining!".format(bot.prefix, index, timeout))
            
        Thread(target=self.timer, args=(timeout,)).start()
        
    def message(self, msg):
        self.bot.send_message(self.channel, msg)
        
    def add_vote(self, voter, vote):
        if voter in self.voted and ONE_PER_USER:
            return False
           
        else:
            self.votes.append(vote)
            self.voted.add(voter)
            return True
        
    def timer(self, timeout):
        time.sleep(timeout)
        
        polls[self.index] = None
        groups = sorted(group(self.votes), reverse=True)
        
        self.message("Time's up for poll #{} '{}'!".format(self.index, self.name))
        
        if len(groups) == 0:
            self.message("The poll bored {} so much that nobody voted!".format(self.channel))
        
        else:
            self.message("Winner vote group has strength {:.3f}: {}".format(groups[0][0], "'" + "', '".join(tuple(groups[0][1])[:5])) + "'")

def stemmed_bigrams(sentence):
    return bigrams("".join([" " + stemmer.stem(i) if not i.startswith("'") and i not in string.punctuation else stemmer.stem(i) for i in nltk.word_tokenize(sentence)]).strip())

def similarity(sentence, sentence2):
    return len(tuple(set(stemmed_bigrams(sentence)) & set(stemmed_bigrams(sentence2)))) \
        / min(len(tuple(bigrams(sentence))), len(tuple(bigrams(sentence))))
    
def group(pool, sentence_bias=0.35, group_bias=0.05):
    groups = []
    negate = set()

    for sentence in pool:
        if sentence in negate:
            continue
    
        g = {sentence}
        strength = []
    
        for sentence2 in pool:
            if sentence2 in negate:
                continue
            
            simi = similarity(sentence, sentence2)
            
            if simi > sentence_bias:
                g.add(sentence2)
                strength.append(simi)
    
        if g not in [x[1] for x in groups] and simi > group_bias:
            groups.append((sum(strength), g)) # no averaging, just summing.
            
            for s in g:
                negate.add(s)
            
    return groups
    
def commands(bot):
    @bot.command("poll", doc="Make a poll! The voting classification is automatic, so you don't need to specify the possible answers.")
    def cmd_poll(bot, conn, evt, args):
        Poll(len(polls), bot, evt.target, ' '.join(args[1:]), float(args[0]))
        
    @bot.command("vote", doc="Vote on a poll! Any answer can be given, as long as it is in English.")
    def cmd_vote(bot, conn, evt, args):
        if len([x for x in polls if x is not None]) < 2:
            id = 0
            
            while polls[id] is None:
                id += 1
            
            vote = ' '.join(args)
        
        else:
            try:
                id = int(args[0])
                
            except ValueError:
                bot.send_message(evt.target, "Invalid ID value.")
                return
                
            vote = ' '.join(args[1:])
        
        if id >= len(polls):
            bot.send_message(evt.target, "No poll of ID #{} exists.".format(id))
            
        elif polls[id] is None:
            bot.send_message(evt.target, "The poll of ID #{} ended a long time ago...".format(id))
            
        elif vote == "":
            bot.send_message(evt.target, "Syntax:   {}vote {} <vote>".format(conn.prefix, id))
            
        else:
            if polls[id].add_vote(evt.source.nick, vote):
                bot.send_message(evt.target, "Vote added with success to poll #{} '{}'! {:.2f} seconds remaining.".format(id, polls[id].name, polls[id].timeout - (time.time() - polls[id].time)))
                
            else:
                bot.send_message(evt.target, "You already voted at poll #{} '{}'! {:.2f} seconds remaining.".format(id, polls[id].name, polls[id].timeout - (time.time() - polls[id].time)))