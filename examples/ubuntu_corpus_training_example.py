import sys
import os

current_directory = os.path.dirname(os.path.abspath(__file__))
parent_directory = os.path.abspath(os.path.join(current_directory, os.pardir))
sys.path.insert(0, parent_directory)

from chatterbot import ChatBot # NOQA
from chatterbot.trainers import UbuntuCorpusTrainer # NOQA
import logging # NOQA
import time # NOQA


'''
This is an example showing how to train a chat bot using the
Ubuntu Corpus of conversation dialog.
'''

# Enable info level logging
logging.basicConfig(level=logging.INFO)

chatbot = ChatBot('Example Bot')

trainer = UbuntuCorpusTrainer(chatbot)

start_time = time.time()

# Start by training our bot with the Ubuntu corpus data
trainer.train()

print('Done training.')
print('Training took', time.time() - start_time, 'seconds.')

# Now let's get a response to a greeting
# response = chatbot.get_response('How are you doing today?')
# print(response)
