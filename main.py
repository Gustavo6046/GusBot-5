"""
GusBot V is the GusBot series' return to
Python land. Apparently Node was not 
very appreciated by Gustavo6046!

== Copyright & Licensing ==
GusBot V is (c)2018 Gustavo R. Rehermann.

Source code: MIT.
Related media: CC-BY.
"""
import logging
import importlib
import traceback
import textwrap
import yaml

import time
from os import path
from glob import glob
from irc.bot import ServerSpec, SingleServerIRCBot
from threading import Thread
    
# Constants
DEFAULT_PREFIX = "[="

# Variables
last_chan = {}
last_interface = {}

# logging.getLogger("irc.client").setLevel(logging.DEBUG)

class GusPIRC5(SingleServerIRCBot):
    def command(self, name, doc="There is no documentation for this command.", group="default"):
        def __decorator__(func):
            def __inner__(bot, conn, evt, args, *_args, **kwargs):
                res = func(bot, conn, evt, args, *_args, **kwargs)
                
                if type(res) in (tuple, list):
                    for m in res:
                        bot.send_message(evt.target, str(m))
                
                elif res is not None:
                    bot.send_message(evt.target, str(res))
                
                return res
                
            self.cgroups[group] = self.cgroups.get(group, set())
            
            if isinstance(name, str):
                self.commands[name] = __inner__
                self.docs[name] = doc
                self.cgroups[group].add(name)
            
            elif type(name) in (list, tuple):
                for n in name:
                    self.commands[n] = __inner__
                    self.docs[n] = doc
                    self.cgroups[group].add(n)
            
            return __inner__

        return __decorator__
         
    def parser(self):
        def __decorator__(func):
            self.parsers.append(func)
            return func

        return __decorator__
        
    def reload(self, reason, event=None):
        bcom = self.commands
        bcgr = self.cgroups
        bdoc = self.docs
        bpar = self.parsers
    
        try:
            self.commands = {}
            self.cgroups = {}
            self.docs = {}
            self.parsers = []
        
            self.default_commands()
            self.import_commands(reason)
            
        except BaseException as e:
            traceback.print_exc()
            
            if event is not None:
                self.send_message(event.target, "[{}: {} reloading! ({})]".format(event.source.nick, type(e).__name__, str(e)))
                
            else:
                raise
            
            self.commands = bcom
            self.cgroups = bcgr
            self.docs = bdoc
            self.parsers = bpar
        
    def import_commands(self, reason):
        for f in glob("commands/*.py"):
            cmd_file = f.replace('\\', '/')
            mod = path.split(cmd_file)[1][:-3]
            
            if mod == "__init__":
                continue
            
            print("[{} | {}] Reading command module: {}".format(self.name, reason, mod))
            
            if mod not in self.modules:
                m = importlib.import_module('commands.' + mod)
                m.commands(self)
                
                self.modules[mod] = m
                
            else:
                importlib.reload(self.modules[mod]).commands(self)
        
        self.imported = True
        
    def __init__(self, name, nick, realname, server, port, channels, account, prefix):
        self.name = name
        self.prefix = prefix
        self.joinchans = channels
        self.account = account
        self.imported = False
        
        self.commands = {}
        self.cgroups = {}
        self.modules = {}
        self.docs = {}
        self.parsers = []
        self.reload("Initializing")
    
        super().__init__([ServerSpec(server, port)], nick, realname)        
        
    def default_commands(self):
        @self.command('doc', doc="Use this command to get information about a command.")
        def doc(bot, conn, evt, args):
            if len(args) < 1:
                bot.send_message(evt.target, "{}: Use the help command to get information about a command, for example, those decribed in the vote command.".format(evt.source.nick))
                return

            command = args[0]
            docstr = docs.get(command, "No such command found!")
            
            bot.send_message(evt.target, "{}: {}".format(evt.source.nick, docstr))
       
        @self.command(('list', 'help'), doc="Use this command to list all the command groups!")
        def list_groups(bot, conn, evt, args):
            bot.send_message(evt.target, "Command groups available: " + ', '.join(tuple(self.cgroups.keys())))
            
        @self.command('group', doc="Use this command to list all the commands inside a group!")
        def get_group_commands(bot, conn, evt, args):
            group = args[0]
            
            if group in self.cgroups:
                bot.send_message(evt.target, "Commands available in group '{}': {}".format(group, ', '.join(self.cgroups[group])))
            
            else:
                bot.send_message(evt.target, "No such command group '{}'!".format(group))
                
        @self.command('reload', doc="Reloads every command!")
        def get_group_commands(bot, conn, evt, args):
            bot.reload("User Reload", evt)
            bot.send_message(evt.target, "Reloaded with success!")
    
    def send_message(self, channel, msg):
        wp = textwrap.wrap(msg, 439 - len(channel))
    
        for i, line in enumerate(wp):
            self.connection.privmsg(channel, line)
            
            if i < len(wp) - 1:
                time.sleep(0.6)    
        
    def on_pubmsg(self, connection, event):
        last_chan[event.source.nick] = event.target
        last_interface[event.source.nick] = self
    
        if event.arguments[0].startswith(self.prefix):
            cmd_full = event.arguments[0][len(self.prefix):]
            cmd_name = cmd_full.split(' ')[0]
            cmd_args = cmd_full.split(' ')[1:]
            
            if cmd_name in self.commands:
                try:
                    print("Executing command: " + cmd_name)
                    self.commands[cmd_name](self, connection, event, cmd_args)
                    
                except Exception as e:
                    self.send_message(event.target, "[{}: {} processing the '{}' command! ({})]".format(event.source.nick, type(e).__name__, cmd_name, str(e)))
                    traceback.print_exc()
                    
        else:
            for p in self.parsers:
                try:
                    p(self, connection, event, event.arguments[0])
        
                except Exception as e:
                    traceback.print_exc()
        
    def on_endofmotd(self, connection, event):
        logging.debug("Joining channels...")
        
        def _joinchan_postwait():           
            time.sleep(1)
            if self.account:
                self.connection.privmsg('NickServ', 'IDENTIFY {} {}'.format(self.account['username'], self.account['password']))
                
            time.sleep(9)
        
            for c in self.joinchans:
                print("[{}] Joining {}".format(self.name, c))
                self.connection.join(c)

        Thread(target=_joinchan_postwait).start()
    
if __name__ == "__main__":
    conns = {}
    threads = []
          
    for s in yaml.load(open("irc.yml").read()):
        conns[s['name']] = GusPIRC5(s['name'], s['nickname'], s['realname'], s['server'], s['port'], s.get('channels', ()), s.get('account', None), s.get('prefix', DEFAULT_PREFIX))
        t = Thread(target=conns[s['name']].start, name="Bot: {}".format(s['name']))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()