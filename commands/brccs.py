import time

times = {}
last_speaker = {}

def commands(bot):
    from BayesRehermann import BayesRehermann
    
    br = BayesRehermann("bayesrehermann.db")

    @bot.command("br_snapshot")
    def get_br_response(bot, conn, evt, args):
        if len(args) < 1:
            return "{}: Syntax: {}br_snapshot <snapshot key>".format(evt.source.nick, bot.prefix)
    
        br.create_snapshot(args[0], message_handler=lambda x: bot.send_message(evt.target, x))
        
    @bot.command("br_respond")
    def get_br_response(bot, conn, evt, args):
        if len(args) < 2:
            return "{}: Syntax: {}br_respond <snapshot key> <input sentence>".format(evt.source.nick, bot.prefix)
    
        return "{}: '{}'".format(evt.source.nick, br.respond(args[0], args[1], evt.source.nick))
    
    @bot.command("br_parse")
    def br_parse_file(bot, conn, evt, args):
        path = ' '.join(args)
        
        if args[1:4] == ':\\'
    
    @bot.command("br_empty")
    def empty_br_data(bot, conn, evt, args):
        global times, last_speaker
    
        br.data = []
        br.conversation_ids = {}
        times = {}
        last_speaker = {}
        return "Done. Cleared all."
    
    @bot.command("br_last")
    def last_br_statement(bot, conn, evt, args):
        id = "{}.{}".format(bot.name, evt.target)
        
        if id in last_speaker:
            return "{1} last spoke at ChanID '{0}': '{2}'".format(id, *last_speaker[id])
            
        else:
            return "Nobody spoke at ChanID '{}' yet.".format(id)
    
    @bot.parser()
    def parse_br_conversation(bot, conn, evt, msg):
        id = "{}.{}".format(bot.name, evt.target)
    
        if id in times and time.time() - times[id] > 240:
            br.reset_id(id)
        
        if id in last_speaker:
            if last_speaker[id][0] == evt.source.nick:
                last_speaker[id] = (evt.source.nick, ' '.join((last_speaker[id][1], msg)))
        
            else:
                br.grow_conversation(id, [last_speaker[id][1]])
                last_speaker[id] = (evt.source.nick, msg)
                
        else:
            last_speaker[id] = (evt.source.nick, msg)
            
        times[id] = time.time()