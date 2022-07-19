import concurrent.futures
import os
import sys

BASE_DIR = os.path.dirname((os.path.abspath(__file__))).replace("\\", "/")
sys.path.append(BASE_DIR)

import reddit_bot
import telegram_bot
import discord_bot

# import whatsappbot
if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executer:
        # executer.submit(whatsappbot.WhatsApp(600).run_script)
        executer.submit(telegram_bot.main)
        executer.submit(reddit_bot.initialize_redditbot)
        executer.submit(discord_bot.bot.run("DISCORD_TOKEN"))
