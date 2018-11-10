import logging
import sys
import os

current_directory = os.path.dirname(os.path.abspath(__file__))
parent_directory = os.path.abspath(os.path.join(current_directory, os.pardir))
sys.path.insert(0, parent_directory)

from chatterbot import ChatBot # NOQA
from chatterbot.trainers import UbuntuCorpusTrainer # NOQA


'''
This is an example showing how to train a chat bot using the
Ubuntu Corpus of conversation dialog.
'''

# Enable info level logging
logging.basicConfig(level=logging.INFO)

chatbot = ChatBot('Example Bot')

trainer = UbuntuCorpusTrainer(chatbot)

# Start by training our bot with the Ubuntu corpus data
trainer.train()

# Now let's get a response to a greeting
# response = chatbot.get_response('How are you doing today?')
# print(response)
