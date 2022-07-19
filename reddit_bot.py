import os
import re
import sys

import praw
from fake_headers import Headers

BASE_DIR = os.path.dirname((os.path.abspath(__file__))).replace("\\", "/")
sys.path.append(BASE_DIR)
from functions_ import fetchCentersData, notification, notify_accepted_str, message_parser, domain, domain2

headers = Headers(headers=True)


def initialize_redditbot():
    print("Starting Reddit Bot")

    reddit = praw.Reddit(
        username='REDDIT_USERNAME',  # The username of your bot
        password='REDDIT_PASSWORD',  # The password to your bots account
        client_id='REDDIT_CLIENTID',  # Your bots client ID
        client_secret='REDDIT_SECRET',  # Your bots client secret
        user_agent='Covistan')  # A short, unique description.

    # the subreddit where the bot is to be live on
    target_sub = "testingground4bots"
    subreddit = reddit.subreddit(target_sub)

    # phrase to trigger the bot
    trigger_phrase = "!"

    # check every comment in the subreddit
    for comment in subreddit.stream.comments(skip_existing=True):

        # check the trigger_phrase in each comment
        if re.match(trigger_phrase, comment.body, re.I):
            # extract the word from the comment
            try:
                comment_text = re.compile(re.escape(trigger_phrase), re.IGNORECASE)
                comment_text = comment_text.sub('', comment.body)
                text = str(comment_text).replace('\\', '').lower()
                if "usage" not in text:
                    data, notify = message_parser(messagestring=text)
                    slot_str, age_str, dose_str, url = notify_accepted_str(userdata=data)
                    if "state_id" in data or "pincode" in data:
                        if notify:
                            if 'email' in data:
                                if any(k in data for k in ("pincode", "state_id", "district_id")):
                                    userdata = notification(rawdata=data, email=True)  # RedditBot not sending DM

                                    reply_text = f"We'll notify you shortly for {slot_str} {age_str} and {dose_str}" \
                                                 f" to {userdata['email']}.\n\n^(Visit this) [^(link)]({url}) " \
                                                 f"^(for more information.)\n\n^(Click this) " \
                                                 f"[^(link)](https://{domain2}/{userdata['code']}) ^(to unsubscribe.)"

                                else:
                                    reply_text = {"error": "Enter more parameters i.e pincode, state, district"}
                            else:
                                reply_text = {"error": "Email required for notification"}
                        else:
                            reply_text = fetchCentersData(maindict=data, redditbot=True)
                            slotstring = f"Total {slot_str} {age_str} and {dose_str}.\n\n"
                            reply_text = slotstring + reply_text + f"\n\n^(Visit this) [^(link)]({url}) " \
                                                                   f"^(for more information.)"
                        if "error" in reply_text:
                            comment.reply(reply_text["error"])
                        else:
                            comment.reply(reply_text)
                    else:
                        str1 = f"\nVisit our [Website](https://{domain}) for more information."
                        str2 = f"\nNo Matching State or District found with name: {text}"
                        str3 = "\nFor slot booking Visit [CoWin](https://selfregistration.cowin.gov.in/)"
                        comment.reply(str2 + str1 + str3)
                else:
                    examplequeries = '''Example Query:\n\n\tAvailable slots:\n\n\t\tEnter "!place name age=18/45 
                    dose=1/2"\n\n\tFor hourly notification:\n\n\t\tAdd "notify"'''
                    comment.reply(examplequeries)
            except Exception as error:
                comment.reply(str(error))
