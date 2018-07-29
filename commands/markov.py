import json
import bs4 as BeautifulSoup
import textwrap
import random
import requests
import re
import time
import threading
import networkx as nx
import multiprocessing
import matplotlib.pyplot as plt
import glob
import os
import difflib

from random import choice, sample
from urllib.parse import urlparse

crawling = 0
crawled  = 0

markov_dict = {}
markov_filter = []

can_crawl = True

def mkplot(markov_dict):
    G = nx.DiGraph()

    labels = {}

    for i, (k, v) in enumerate(tuple(markov_dict.items())):
        G.add_node(k)

        for w in v:
            G.add_node(w)

    for i, (k, v) in enumerate(tuple(markov_dict.items())):
        for w in v:
            G.add_edge(k, w)

    pos = nx.spring_layout(G)

    nx.draw_networkx_nodes(G, pos)
    nx.draw_networkx_edges(G, pos, arrows=True)
    nx.draw_networkx_labels(G, pos, {w: w for k, v in markov_dict.items() for w in [x for x in [k] + list(v)]})

    plt.show()

def hastebin(data):
    data = '\n'.join(['\n'.join(textwrap.wrap(d, 145)) for d in data.splitlines()]).encode('utf-8')

    try:
        h = requests.post("https://hastebin.com/documents", data=data, timeout=10)

    except requests.exceptions.ConnectTimeout:
        return "\x01"

    if h.status_code != 200:
        return "\x02" + str(h.status_code)

    return "\x03http://hastebin.com/" + json.loads(h.text)['key']

def botbin(data, description="Result"):
    r = hastebin(data)

    if r == "\x01":
        return "Error: Connection to hastebin.com timed out!"

    elif r.startswith("\x02"):
        return "Error: Unsuccesful status code reached! ({})".format(r[1:])

    else:
        return "{} URL: {}".format(description, r[1:])

def commands(bot):
    @bot.command("hastemarkovjson")
    def hastemarkov(bot, conn, evt, args):
        return botbin(json.dumps({x: list(y) for x, y in markov_dict.items()}, indent=4))

    @bot.command("hastemarkov")
    def hastemarkov(bot, conn, evt, args):
        if len(markov_dict) == 0:
            return "No entries in the Markov database!"
    
        data = ""
        
        while len(data) < 12000:
            data += do_markov(args[0] if len(args) > 0 else random.choice(tuple(markov_dict.keys())), 2000) + "\r\n\r\n"
            
        return botbin(data)

    @bot.command("listmarkovfiles")
    def list_markov_files(bot, conn, evt, args):
        return botbin("\n".join([os.path.splitext(os.path.split(x)[-1])[0] for x in glob.glob("markov/*.mk5")]))

    @bot.command("qlistmarkovfiles")
    def quick_list(bot, conn, evt, args):
        return "Markov files that can be loaded using loadmarkov: {}".format(", ".join([os.path.splitext(os.path.split(x)[-1])[0] for x in glob.glob("markov/*.mk5")]))

    @bot.command("searchmarkovfiles")
    def search_files(bot, conn, evt, args):
        if len(args) < 1:
            return "Syntax: searchmarkofiles <keyword>"

        return "Similiar Markov files: {} | Markov files with {} in filename: {}".format(", ".join([x for x in [os.path.splitext(os.path.split(x)[-1])[0] for x in glob.glob("markov/*.mk5")] if difflib.guenceMatcher(None, x, " ".join(args[0:])).ratio() > 0.8]), args[0], ", ".join(x for x in [os.path.splitext(os.path.split(x)[-1])[0] for x in glob.glob("markov/*.mk5")] if args[0] in x))

    @bot.command("markovderivates")
    def derivates(bot, conn, evt, args):

        if len(args) < 1:
            return "Syntax: markovderivates <Markov keyword>"

        if args[0] not in markov_dict:
            return "Error: No such word in Markov data!"

        return "Derivates for {}: {}".format(args[0], ", ".join(markov_dict[args[0]]))

    def regex(value, reg):
        if reg == "":
            return True

        return bool(re.match(reg, value))


    def ends_with_any(string, list_of_endings):
        for ending in list_of_endings:
            if string.endswith(ending):
                return True

        return False

    def visible(element):
        if element.parent.name in ['style', 'script', '[document]', 'head', 'title']:
            return False
        elif re.match('<!--.*-->', str(element)):
            return False
        return True

    def isalnumspace(string):
        for char in string:
            if not (char.isalnum() or " " == char):
                return False

        return True

    def simple_string_filter(old_string, bad_chars=None, extra_filter=None):
        result = ""

        if bad_chars:
            for char in old_string:
                if not char in bad_chars:
                    result += char

        if extra_filter and hasattr(extra_filter, "__call__"):
            old_result = result
            result = ""

            for char in old_result:
                if extra_filter(char):
                    result += char

        return result

    def parse_markov_string(string):
        global markov_dict

        words = simple_string_filter(string, "\'\"-/\\,.!?", isalnumspace).split(" ")

        for x in range(len(words)):
            try:
                if words[x - 1] == words[x] or words[x] == words[x + 1]:
                    continue
            except IndexError:
                pass

            try:
                markov_dict[words[x - 1].lower()].add(words[x].lower())
            except KeyError:
                try:
                    markov_dict[words[x - 1].lower()] = {words[x].lower()}
                except IndexError:
                    pass
            except IndexError:
                pass

            try:
                markov_dict[words[x].lower()].add(words[x + 1].lower())
            except KeyError:
                try:
                    markov_dict[words[x].lower()] = {words[x + 1].lower()}
                except IndexError:
                    pass
            except IndexError:
                continue

    def string_filter(old_string, filter_, separator=None):
        result_string = []

        if hasattr(filter_, "__call__"):
            for x in old_string:
                if filter_(x):
                    result_string.append(x)

        else:
            if separator is None:
                for x in old_string:
                    if x in str(filter_):
                        result_string.append(x)
            else:
                for x in old_string:
                    if x in str(filter_).split(separator):
                        result_string.append(x)

        return "".join(result_string)

    def do_markov(x, max_len=320):
        global markov_dict

        for key, item in markov_dict.items():
            markov_dict[key] = set(item)

        # Checks.
        try:
            markov_dict.__delitem__("")
            markov_dict.__delitem__(" ")

        except KeyError:
            pass

        for i, mkv in markov_dict.items():
            try:
                markov_dict[i].remove(" ")
                markov_dict[i].remove("")

            except KeyError:
                continue

        if len(markov_dict) < 1:
            return "Error: no Markov data!"

        words = [x]
        level = 0
        result = x

        # print x

        while level < len(words) - 1:
            if not words[level + 1] in markov_dict[x]:
                return ["{}: {}".format(evt.source.nick, result)]

            x = words[level + 1]
            level += 1
            result += " " + x

        while x in markov_dict.keys():
            try:
                x = sample(markov_dict[x], 1)[0]

            except ValueError:
                break

            # print x.encode("utf-8")

            result += " " + x

            if len(result) > max_len:
                break

        for cuss in markov_filter:
            result = result.replace(cuss, "#" * len(cuss))
            
        return result
        
    def crawl_markov(website, url_mask, max_level=3, level=0, crawled_urls=[]):
        global markov_dict
        global crawling, crawled

        print("{}{}Crawling {}...".format("| " * level, "+ ", website))
        crawling += 1

        if level > max_level:
            return

        if not can_crawl:
            return

        warnings = []
        time.sleep(0.4)

        try:
            request = requests.get(website.encode("utf-8"), timeout=10)

        except requests.ConnectionError:
            return

        except requests.exceptions.Timeout:
            return

        except (requests.exceptions.MissingSchema, requests.exceptions.InvalidURL):
            try:
                request = requests.get("http://" + website.encode("utf-8"), timeout=10)

            except requests.ConnectionError:
                return

            except requests.exceptions.Timeout:
                return

            except requests.exceptions.InvalidURL:
                return

        html = BeautifulSoup.BeautifulSoup(request.text)

        if level < max_level:
            for link in html.find_all("a"):
                url = link.get("href")
                
                if url is None:
                    continue
                
                print("{} [{}] Checking URL: {}".format("| " * (level + 1), website, url))
                
                if url.startswith("/"):
                    psd = urlparse(website, scheme="http")
                    url = "{}://{}/{}".format(psd.scheme, psd.netloc, url)

                if re.match("\.[a-zA-Z1-9]+$", url) and not any(url.endswith(x) for x in [".html", ".php", ".htm"]):
                    continue

                if not url.startswith("http"):
                    continue

                if url in crawled_urls:
                    continue

                crawled_urls.append(url)

                if regex(url, url_mask):
                    threading.Thread(target=crawl_markov, args=(url, url_mask, max_level, level+1, crawled_urls)).start()

        for visible_text in [text for text in filter(visible, html.findAll(text=True))]:
            for line in visible_text.splitlines():
                parse_markov_string(line)

        time.sleep(0.5)
        crawled += 1

        print("{}{}Done crawling {}!".format("| " * level, "^ ", website))

    @bot.command("plotmarkov")
    def plot_markov(bot, conn, evt, args):
        global markov_dict

        p = multiprocessing.Process(target=mkplot, args=(markov_dict,))
        p.start()

        return "Plotting..."

    @bot.command("togglemarkovcrawling")
    def toggle_crawling(bot, conn, evt, args):
        global can_crawl

        can_crawl = not can_crawl

        return "Success: now crawling is{} stopped!".format(("n't" if can_crawl else ""))

    @bot.command("parsemarkov")
    def parse_markov_text(bot, conn, evt, args):
        global markov_dict

        for key, item in markov_dict.items():
            markov_dict[key] = set(item)

        if True: # GusBot2 compatibility layer
            if len(args) < 1:
                bot.send_message(evt.target, "{}: Error: No argument provided!".format(evt.source.nick))

            data = open(" ".join(args[0:])).read()
            data = " ".join([n.strip() for n in data.split("\n")])

            words = [x for x in simple_string_filter(data, "\'\"-/\\,.!?", isalnumspace).split(" ") if x != " "]

            for x in range(len(words)):
                try:
                    if words[x - 1] == words[x] or words[x] == words[x + 1]:
                        continue

                except IndexError:
                    pass


                try:
                    markov_dict[words[x - 1].lower()].add(words[x].lower())

                except KeyError:
                    try:
                        markov_dict[words[x - 1].lower()] = {words[x].lower()}
                        
                    except IndexError:
                        pass

                except IndexError:
                    pass


                try:
                    markov_dict[words[x].lower()].add(words[x + 1].lower())

                except KeyError:
                    try:
                        markov_dict[words[x].lower()] = {words[x + 1].lower()}
                        
                    except IndexError:
                        pass

                except IndexError:
                    continue

            bot.send_message(evt.target, "{}: Text file succesfully parsed on Markov!".format(evt.source.nick))

    @bot.command("flushmarkov")
    def flush_markov_data(bot, conn, evt, args):
        global markov_dict

        markov_dict = {}

        return ["Markov flushed succesfully!"]

    @bot.parser()
    def feed_markov_data(bot, conn, evt, msg):
        global markov_dict

        for key, item in markov_dict.items():
                markov_dict[key] = set(item)

        words = simple_string_filter(msg, "\'\"-/\\,.!?", isalnumspace).split(" ")

        for x in range(len(words)):
            if x - 1 > -1:
                try:
                    if words[x - 1] == words[x] or words[x] == words[x + 1]:
                        continue
                except IndexError:
                    pass

                try:
                    markov_dict[words[x - 1].lower()].add(words[x].lower())
                except KeyError:
                    try:
                        markov_dict[words[x - 1].lower()] = {words[x].lower()}
                    except IndexError:
                        pass
                except IndexError:
                    pass

                try:
                    markov_dict[words[x].lower()].add(words[x + 1].lower())
                except KeyError:
                    try:
                        markov_dict[words[x].lower()] = {words[x + 1].lower()}
                    except IndexError:
                        pass
                except IndexError:
                    continue

            else:
                try:
                    markov_dict[words[x].lower()].add(words[x + 1].lower())
                except KeyError:
                    try:
                        markov_dict[words[x].lower()] = {words[x + 1].lower()}
                    except IndexError:
                        pass
                except IndexError:
                    continue

    @bot.command("markov")
    def get_markov(bot, conn, evt, args):
        if len(markov_dict) == 0:
            return "No entries in the Markov database!"
    
        result = do_markov(args[0] if len(args) > 0 else random.choice(tuple(markov_dict.keys())))
        result = "{0}: '{1}'".format(evt.source.nick, result)

        return [result]

    @bot.command("savemarkov")
    def save_markov_json(bot, conn, evt, args):
        global markov_dict

        if True: # GusBot2 compatibility layer
            if len(args) < 1:
                return ["Error: not enough arguments!", "(Insert Markov file name as an argument)"]

            save_dict = markov_dict

            for key, item in save_dict.items():
                save_dict[key] = tuple(item)

            open("markov/{}.mk5".format(args[0]), "w").write(json.dumps(save_dict))

            for key, item in markov_dict.items():
                markov_dict[key] = set(item)

            return ["{}: Saved succesfully to {}.mk5!".format(evt.source.nick, args[0])]

        else:
            return []

    @bot.command("loadmarkovfilter")
    def load_markov_filter(bot, conn, evt, args):
        global markov_filter

        if len(args) < 1:
            return ["Error: Not enough arguments!"]

        markov_filter += open("filters/{}.mk5f".format(" ".join(args[1:]))).readlines()

        return ["Blacklist updated succesfully!"]

    @bot.command("savemarkovfilter")
    def save_markov_filter(bot, conn, evt, args):
        global markov_filter

        if len(args) < 1:
            return ["Error: Not enough arguments!"]

        open("filters/{}.mk5f".format(" ".join(args[1:])), "w").write("\n".join(markov_filter))

        return ["Blacklist updated succesfully!"]

    @bot.command("loadmarkov")
    def load_markov_json(bot, conn, evt, args):
        global markov_dict

        if True: # GusBot2 compatibility layer
            if len(args) < 1:
                return ["Error: not enough arguments!", "(Insert Markov file name as an argument)"]

            new_dict = json.load(open("markov/{}.mk5".format(args[0])))

            for key, item in new_dict.items():
                new_dict[key] = {word for word in item}

            markov_dict.update(new_dict)

            return ["Loaded succesfully from {}.mk5!".format(args[0])]

        else:
            return []

    @bot.command("listfiltermarkov")
    def list_cusses(bot, conn, evt, args):
        return "Cusses blacklisted: " + ", ".join(markov_filter)

    @bot.command("addfiltermarkov")
    def filter_cusses(bot, conn, evt, args):
        global markov_filter

        try:
            markov_filter += args[1:]
            return ["Updated word blacklist succesfully!"]

        except IndexError:
            return ["Syntax: addfiltermarkov <list of cusses or blacklisted words>"]

    @bot.command("removefiltermarkov")
    def unfilter_cusses(bot, conn, evt, args):
        global markov_filter

        try:
            for cuss in args[1:]:
                markov_filter.remove(cuss)

            return ["Updated word blacklist succesfully!"]

        except IndexError:
            return ["Syntax: removefiltermarkov <list of words to un-blacklist>"]

    @bot.command("webmarkov")
    def parse_web_markov(bot, conn, evt, args):
        global markov_dict

        for key, item in markov_dict.items():
            markov_dict[key] = set(item)

        messages = []
        warnings = []

        debug = "--debug" in args

        if len(args) < 1:
            return ["{}: Error: No argument provided! (Syntax: parsewebmarkov <list of URLs>)".format(evt.source.nick)]

        for website in filter(lambda x: not x.startswith("--"), args):
            print("Parsing Markov from {}!".format(website))
            messages.append("Parsing Markov from {}!".format(website))

            try:
                request = requests.get(website, timeout=10)

            except requests.ConnectionError:
                warnings.append("Error with connection!")

                if debug:
                        raise

            except requests.exceptions.Timeout:
                warnings.append("Connection timed out!")

                if debug:
                        raise

            except requests.exceptions.MissingSchema:
                try:
                    request = requests.get("http://" + website, timeout=10)

                except requests.ConnectionError:
                    warnings.append("Error with connection!")

                    if debug:
                        raise

                except requests.exceptions.Timeout:
                    warnings.append("Connection timed out!")

                    if debug:
                        raise

            if not "request" in locals().keys():
                continue

            if request.status_code != 200:
                er = "{}: Error: Status {} reached!".format(evt.source.nick, request.status_code)
                warnings.append(er)
                messages.append(er)
                continue

            visible_texts = filter(visible, BeautifulSoup.BeautifulSoup(request.text).findAll(text=True))

            lines = []

            for text in visible_texts:
                lines += text.split("\n")

            for line in lines:
                words = simple_string_filter(line, "\'\"-/\\,.!?", isalnumspace).split(" ")

                for x in range(len(words)):
                    try:
                        if words[x - 1] == words[x] or words[x] == words[x + 1]:
                            continue
                    except IndexError:
                        pass

                    try:
                        markov_dict[words[x - 1].lower()].add(words[x].lower())
                    except KeyError:
                        try:
                            markov_dict[words[x - 1].lower()] = {words[x].lower()}
                        except IndexError:
                            pass
                    except IndexError:
                        pass

                    try:
                        markov_dict[words[x].lower()].add(words[x + 1].lower())
                    except KeyError:
                        try:
                            markov_dict[words[x].lower()] = {words[x + 1].lower()}
                        except IndexError:
                            pass
                    except IndexError:
                        continue

        if len(warnings) < len(args):
            messages.append("{}: Success reading Markov from (some) website(s)!".format(evt.source.nick))

        return messages

    @bot.command("clearmarkovfilter")
    def clear_filter(bot, conn, evt, args):
        global markov_filter

        markov_filter = []
        return "Success clearing Markov filter!"

    @bot.command("purgemarkov")
    def purge_word_from_markov(bot, conn, evt, args):
        global markov_dict

        if len(args) < 1:
            return "Syntax: purgemarkov <list of words to purge from Markov>"

        for word in args[1:]:
            for kw in markov_dict.keys():
                if kw == word:
                    markov_dict.__delitem__(kw)

                try:
                    if word in markov_dict[kw]:
                        markov_dict[kw] = [mk for mk in markov_dict[kw] if mk != word]

                        if markov_dict[kw] == []:
                            markov_dict.__delitem__(kw)

                except KeyError:
                    pass

        return "Words purged from Markov succesfully!"

    def check_crawled(bot, conn, evt, args):
        global crawling, crawled

        time.sleep(1.5)
        
        while crawling > crawled:
            time.sleep(0.5)

        bot.send_message(
            evt.target,
            "Finished crawling {all} websites!".format(all=crawled)
        )

    @bot.command("webmarkovcrawl")
    def get_web_markov_crawling(bot, conn, evt, args):
        global crawling, crawled

        def smsg(msg):
            if type(msg) is str:
                bot.send_message(
                    evt.target,
                    msg
                )

                return True

            elif hasattr(msg, "__iter__"):
                for m in msg:
                    bot.send_message(
                        evt.target,
                        m
                    )

                return True

            else:
                return False

        crawling = 0
        crawled  = 0

        time.sleep(0.3)

        if len(args) < 3:
            smsg("Syntax: <URL mask> <max level> <list of URLs to crawl for Markov>")
            return

        try:
            if int(args[1]) > 4:
                smsg("Way too large value for max_level! Use only up to 4. Do you want to wait for an eternity?!?")
                return

            if int(args[1]) < 0:
                smsg("LOL! Negative level!")
                return

        except ValueError:
            smsg("Insert some int for max level (second argument)! Insert something between 0 and 4.")
            return

        for website in args[2:]:
            crawl_markov(website, args[0], int(args[1]))

        smsg("Website crawling threads started! Check for new additions using {}markovsize .".format(bot.prefix))
        threading.Thread(target=check_crawled, args=(bot, conn, evt, args)).start()

    @bot.command("markovsize")
    def get_markov_size(bot, conn, evt, args):
        global markov_dict

        if True: # GusBot2 compatibility layer
            return ["Size of Markov chain: {}".format(len(markov_dict))]
