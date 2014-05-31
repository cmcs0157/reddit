import praw # simple interface to the reddit API, also handles rate limiting of requests
import time
import os
import sys
import sqlite3

'''USER CONFIGURATION'''
USERNAME  = ""
#This is the bot's Username. In order to send mail, he must have some amount of Karma.
PASSWORD  = ""
#This is the bot's Password. 
USERAGENT = ""
#This is a short description of what the bot does. For example "/u/GoldenSights' Newsletter bot"
SUBREDDIT = "all"
#This is the sub or list of subs to scan for new posts. For a single sub, use "sub1". For multiple subreddits, use "sub1+sub2+sub3+..."
TITLE = "Newsletteryly"
#This is the title of every message sent by the bot.
FOOTER = "[In operating BotBotBot](http://redd.it/26xset)"
#This will be the footer of every message sent by the bot.
MAXPOSTS = 100
#This is how many posts you want to retreieve all at once. PRAW will download 100 at a time.
WAIT = 10
#This is how many seconds you will wait between cycles. The bot is completely inactive during this time.

'''All done!'''





try:
    import bot #This is a file in my python library which contains my Bot's username and password. I can push code to Git without showing credentials
    USERNAME = bot.getu()
    PASSWORD = bot.getp()
    USERAGENT = bot.geta()
except ImportError:
    pass
WAITS = str(WAIT)


sql = sqlite3.connect('sql.db')
print('Loaded SQL Database')
cur = sql.cursor()

cur.execute('CREATE TABLE IF NOT EXISTS oldposts(ID TEXT)')
print('Loaded Completed table')

cur.execute('CREATE TABLE IF NOT EXISTS subscribers(name TEXT, reddit TEXT)')
print('Loaded Subscriber table')

sql.commit()


r = praw.Reddit(USERAGENT)
r.login(USERNAME, PASSWORD) 

def updateSubs():
    global SUBREDDIT
    sublist = []
    cur.execute('SELECT * FROM subscribers')
    for sub in cur.fetchall():
        if sub[1] not in sublist:
            sublist.append(sub[1])
    if len(sublist) > 0:
        SUBREDDIT = '+'.join(sublist)

def countTable(table):
    cur.execute("SELECT * FROM '%s'" % table)
    c = 0
    while True:
        row = cur.fetchone()
        if row == None:
            break
        else:
            c += 1
    return c

def scanSub():
    print('Searching '+ SUBREDDIT + '.')
    subreddit = r.get_subreddit(SUBREDDIT)
    userlist = []
    cur.execute('SELECT * FROM subscribers')
    for user in cur.fetchall():
        if user[0] not in userlist:
            userlist.append(user[0])
    for user in userlist:
        print('Finding posts for ' + user)
        usersubs = []
        result = []
        cur.execute('SELECT * FROM subscribers WHERE name="%s"' % user)
        f = cur.fetchall()
        for m in f:
            usersubs.append(m[1])
        for post in subreddit.get_new(limit=MAXPOSTS):
            cur.execute('SELECT * FROM oldposts WHERE ID="%s"' % post.id)
            if not cur.fetchone():
                if post.subreddit.display_name.lower() in usersubs:
                    print('\t' + post.id)
                    result.append(post.permalink)
        if len(result) > 0:
            result.append('___\n\n' + FOOTER)
            r.send_message(user, TITLE, 'Your subscribed subreddits have had some new posts: \n\n' + '\n\n'.join(result), captcha=None)
    for post in subreddit.get_new(limit=MAXPOSTS):
        cur.execute('SELECT * FROM oldposts WHERE ID="%s"' % post.id)
        if not cur.fetchone():
            cur.execute('INSERT INTO oldposts VALUES("%s")' % post.id)
    sql.commit()



def scanPM():
    print('Searhing Inbox.')
    pms = r.get_unread(unset_has_mail=True, update_user=True)
    for pm in pms:
        result = []
        author = pm.author.name
        bodysplit = pm.body.lower().split('\n\n')
        if len(bodysplit) <= 10:
            for line in bodysplit:
                linesplit = line.split()
                command = linesplit[0]
                args = []
                try:
                    linesplit = linesplit[1:]
                    for string in linesplit:
                        args.append(string.replace(',',''))
                except Exception:
                    args.append('')
    
        
                if args:
                    for arg in args:
                        print(author + ': ' + command + ' ' + arg)
                        if command == 'subscribe':
                            try:
                                s = r.get_subreddit(arg, fetch=True)
                                cur.execute('SELECT * FROM subscribers WHERE name="%s" AND reddit="%s"' % (author, arg))
                                if not cur.fetchone():
                                    #print('New Subscriber: ' + author + ' to ' + arg)
                                    cur.execute('INSERT INTO subscribers VALUES("%s", "%s")' % (author, arg))
                                    result.append('You have successfully registered in the Newsletter database to receive /r/' + arg)
                                else:
                                    print(author + ' is already subscribed to ' + arg)
                                    result.append('You are already registered in the Newsletter database to receive /r/' + arg + '. Maybe you meant to Unsubscribe or try a different subreddit')
                            except Exception:
                                print(author + ' attempted to subscribe to ' + arg + ' but failed.')
                                result.append('We were unable to find any subreddit by the name of /r/' + arg + '. Please confirm that it is spelled correctly and is a public subreddit.')
                
                        if command == 'unsubscribe':
                            if arg == 'all':
                                #print('Lost Subscriber: ' + author + ' from ' + arg)
                                cur.execute('DELETE FROM subscribers WHERE name = "%s"' % author)
                                result.append('You have been removed from all subscriptions.')
                            else:
                                cur.execute('SELECT * FROM subscribers WHERE name="%s" AND reddit="%s"' % (author, arg))
                                if cur.fetchone():
                                    #print('Lost Subscriber: ' + author + ' from ' + arg)
                                    cur.execute('DELETE FROM subscribers WHERE name = "%s" AND reddit = "%s"' % (author, arg))
                                    result.append('You will no longer receive /r/' + arg)
                                else:
                                    print(author + ' is not subscribed to ' + arg)
                                    result.append('You are not registered in the Newsletter database to receive /r/' + arg + '. Maybe you meant to Subscribe or try a different subreddit')
            
                elif command == 'report':
                    print(author + ': report')
                    s = ''
                    cur.execute('SELECT * FROM subscribers WHERE name="%s"' % author)
                    f = cur.fetchall()
                    for m in f:
                        s = s + '/r/' + m[1] + '\n\n'
                    if s == '':
                        s += 'None!'
                    result.append('You have requested a list of your Newsletter subscriptions.\n\n' + s)
                else:
                    result.append("The command '" + command + "' doesn't seem to comply with proper syntax")
                result.append('\n\n_____')
                sql.commit()
            result.append(FOOTER)
            r.send_message(author, TITLE, '\n\n'.join(result), captcha=None)

        else:
            r.send_message(author, 'Newsletteryly', 'Your message was too long.\n\n' + FOOTER)
            print(author + ': Message was too long')
        pm.mark_as_read()
    sql.commit()
    print('')


while True:
    #updateSubs()
    scanPM()
    scanSub()
    print(str(countTable('subscribers')) + ' active subscriptions.')
    print('Running again in ' + WAITS + ' seconds \n')
    sql.commit()
    time.sleep(WAIT)
