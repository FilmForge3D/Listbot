#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import pickle
import os
from random import randint

from telegram.ext import Updater, CommandHandler, MessageHandler

#Version 0.1.6 of the bot

#Fix Relativ Path
os.chdir(os.path.dirname(__file__))

#Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)



#Checks a String if it is an int
def is_number(s):
    try:
        int(s)
        return True
    except ValueError:
        return False



#Sends the help message
def help(update, context):
    
    context.bot.send_message(chat_id=update.effective_chat.id, text=
"""Please note that the lists are not encrypted.
For a tidier use in groups this bot is able to use the 'delete message' permission.
Use '/add' to add items to your list.
Use '/list' to show your current list. You can specify a starting point by adding a number after the '/list' command.
Use '/remove' in combination with the item number to remove an item from the list. '/remove drawn' will remove all previously drawn entries.
Use '/draw' to draw a random list entry. You can draw several items at once by following the '/draw' command with the desired number of items.
Use '/undraw' to remove drawn marker from an item by stating its number or '/undraw all' to reset all drawn flags.
Use '/edit' in combination with the item number and the new item to replace an entry.
All editing commands can be used with a '2' or a '3' right after the command (without a space) to access a second list.""")

    # deletes the request
    context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id) 



#adds entry to the list
def add(update, context):
    
    #working variables
    currentList = []
    
    #checks for existing list file
    try:
        file = open("./lists/" + str(update.effective_chat.id), "rb")
        currentList = pickle.load(file)
        file.close()
    except:
        ()
    #splits message String
    message = update.message.text.split()
    
    #error if no entry is sent
    if len(message) == 1:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Please send the item you want to add to the list after the '/add' command.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    
    #appends the list by the new entry
    del message[0]
    currentList.append(' '.join(message))
    
    #saves the list back to the file
    file = open("./lists/" + str(update.effective_chat.id), "wb")
    pickle.dump(currentList, file)
    file.close()
    
    #confirmation message
    context.bot.send_message(chat_id=update.effective_chat.id, text="✅ " + update.effective_user.first_name + " added " + str(len(currentList)) + ": '" + " ".join(message) + "'")
    context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)


def add2(update, context):
    
    #working variables
    currentList = []
    
    #checks for existing list file
    try:
        file = open("./lists/" + str(update.effective_chat.id) + "-2", "rb")
        currentList = pickle.load(file)
        file.close()
    except:
        ()
    #splits message String
    message = update.message.text.split()
    
    #error if no entry is sent
    if len(message) == 1:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Please send the item you want to add to the list after the '/add2' command.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    
    #appends the list by the new entry
    del message[0]
    currentList.append(' '.join(message))
    
    #saves the list back to the file
    file = open("./lists/" + str(update.effective_chat.id) + "-2", "wb")
    pickle.dump(currentList, file)
    file.close()
    
    #confirmation message
    context.bot.send_message(chat_id=update.effective_chat.id, text="List 2 ✅ " + update.effective_user.first_name + " added " + str(len(currentList)) + ": '" + " ".join(message) + "'")
    context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)


def add3(update, context):
    
    #working variables
    currentList = []
    
    #checks for existing list file
    try:
        file = open("./lists/" + str(update.effective_chat.id) + "-3", "rb")
        currentList = pickle.load(file)
        file.close()
    except:
        ()
    #splits message String
    message = update.message.text.split()
    
    #error if no entry is sent
    if len(message) == 1:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Please send the item you want to add to the list after the '/add3' command.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    
    #appends the list by the new entry
    del message[0]
    currentList.append(' '.join(message))
    
    #saves the list back to the file
    file = open("./lists/" + str(update.effective_chat.id) + "-3", "wb")
    pickle.dump(currentList, file)
    file.close()
    
    #confirmation message
    context.bot.send_message(chat_id=update.effective_chat.id, text="List 3 ✅ " + update.effective_user.first_name + " added " + str(len(currentList)) + ": '" + " ".join(message) + "'")
    context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)



#same as add but an insider version
def grupp(update, context):
    
	#working variables
    currentList = []
	
    try:
        file = open("./lists/" + str(update.effective_chat.id), "rb")
        currentList = pickle.load(file)
        file.close()
    except:
        ()
        
    message = update.message.text.split()
    
    if len(message) == 1:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Das was gegruppt werden soll kommt nach dem '/grupp' Befehl.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    
    del message[0]
    currentList.append(' '.join(message))
    
    file = open("./lists/" + str(update.effective_chat.id), "wb")
    pickle.dump(currentList, file)
    file.close()
    
    context.bot.send_message(chat_id=update.effective_chat.id, text="✅ " + update.effective_user.first_name + " hat '" + ' '.join(message) + "' als " + str(len(currentList)) + ". gegruppt.")
    context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)


def grupp2(update, context):
    
	#working variables
    currentList = []
	
    try:
        file = open("./lists/" + str(update.effective_chat.id) +"-2", "rb")
        currentList = pickle.load(file)
        file.close()
    except:
        ()
        
    message = update.message.text.split()
    
    if len(message) == 1:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Das was gegruppt werden soll kommt nach dem '/grupp2' Befehl.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    
    del message[0]
    currentList.append(' '.join(message))
    
    file = open("./lists/" + str(update.effective_chat.id) + "-2", "wb")
    pickle.dump(currentList, file)
    file.close()
    
    context.bot.send_message(chat_id=update.effective_chat.id, text="Liste 2 ✅ " + update.effective_user.first_name + " hat '" + ' '.join(message) + "' als " + str(len(currentList)) + ". gegruppt.")
    context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)


def grupp3(update, context):
    
	#working variables
    currentList = []
	
    try:
        file = open("./lists/" + str(update.effective_chat.id) +"-3", "rb")
        currentList = pickle.load(file)
        file.close()
    except:
        ()
        
    message = update.message.text.split()
    
    if len(message) == 1:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Das was gegruppt werden soll kommt nach dem '/grupp3' Befehl.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    
    del message[0]
    currentList.append(' '.join(message))
    
    file = open("./lists/" + str(update.effective_chat.id) + "-3", "wb")
    pickle.dump(currentList, file)
    file.close()
    
    context.bot.send_message(chat_id=update.effective_chat.id, text="Liste 3 ✅ " + update.effective_user.first_name + " hat '" + ' '.join(message) + "' als " + str(len(currentList)) + ". gegruppt.")
    context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)



#removes entries from the list
def remove(update, context):
    
    #working variables
    currentList = []
    removedList = []
    items = ""
    
    #tries to open the list file
    try:
        file = open("./lists/" + str(update.effective_chat.id), "rb")
    except: #throws an error if there is no file
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Your currently do not have a list to remove from.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    currentList = pickle.load(file)
    file.close()

    #splits message String
    message = update.message.text.split()
    
    #throws an error if there is no specification what to remove
    if len(message) == 1:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ To remove an entry from the list enter a number after the '/remove' command. To remove all previously drawn entries use '/remove drawn'.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    
    #checks if the specifier is 'drawn', if not it throws an error
    if not message[1]=="drawn":
        if not is_number(message[1]):
            context.bot.send_message(chat_id=update.effective_chat.id, text="❌ To remove an entry from the list enter a number after the '/remove' command. To remove all previously drawn entries use '/remove drawn'.")
            return
        
    #checks if the specifier is a number
    if is_number(message[1]):
        
        #throws an error if the specifier exceeds the list lenght
        if int(message[1]) > len(currentList):
            context.bot.send_message(chat_id=update.effective_chat.id, text="❌ There is no item number " + message[1] + " in your list.")
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
            return
        
        #keeps entry in woking wariable
        items = currentList[int(message[1])-1]
		
		#deletes the entry from the working list
        del currentList[int(message[1])-1]
        
        #tries to open the drawn index
        try:
            file = open("./lists/" + str(update.effective_chat.id) + "drawn", "rb")
            drawnList = pickle.load(file)
            file.close()
            
            #tries to remove the index from the drawn index
            try:
                drawnList.remove(int(message[1])-1)
            except:
                ()
            else:#saves the edited drawn index
                file = open("./lists/" + str(update.effective_chat.id) + "drawn", "wb")
                pickle.dump(drawnList, file)
                file.close()
        except:
            ()
    
    #precedure to remove all drawn entries
    if message[1]=="drawn":
        	
		
        #checks if there is an list of drawn indexes
        try:
            file = open("./lists/" + str(update.effective_chat.id) + "drawn", "rb")
        except:
            context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Your currently do not have any previously drawn entries.")
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
            return
        drawnList = pickle.load(file)
        file.close()
        
        #loops throught the drawn indexes and apends the message
        for i in range(len(drawnList)):
            items += "\n" + str(drawnList[i] + 1) + ": " + currentList[drawnList[i]]
			
	    #keeps track of which entries were removed
            removedList.append(drawnList[i])
			
	    #breaks list appending when max message length is near and informs user
            if len(items)> 3584:
                items += "\n❌ You have to many drawn entries. Only removing the first " + str(i + 1)
                break
			
	#sorts drawn List in decending order to only delete correct entries
        removedList.sort(reverse = True)
	
	#loops throught the drawn indexes and removes the entries
        for i in range(len(removedList)):
		
	    #removes all removed entries from the list
            del currentList[removedList[i]]
		
	    #removes all removed entries from the drawn list
            drawnList.remove(removedList[i])
		
        #saves the empty list
        file = open("./lists/" + str(update.effective_chat.id) + "drawn", "wb")
        pickle.dump(drawnList, file)
        file.close()
        
        #detetes any old drawn list
        try:
            os.remove("./lists/" + str(update.effective_chat.id) + "drawn_old")
        except:
            ()
            
        #archives the emptied list
        os.rename("./lists/" + str(update.effective_chat.id) + "drawn" , "./lists/" + str(update.effective_chat.id) + "drawn_old")
    
    #saves the shortened working list to the list file
    file = open("./lists/" + str(update.effective_chat.id), "wb")
    pickle.dump(currentList, file)
    file.close()
    
    #sends the message for specific entry removal
    if is_number(message[1]):
        context.bot.send_message(chat_id=update.effective_chat.id, text="✅ " + update.effective_user.first_name + " removed " + message[1] + ": '" + items + "'")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
    
    #sends the message for drawn entry
    if message[1]=="drawn":
        context.bot.send_message(chat_id=update.effective_chat.id, text="✅ " + update.effective_user.first_name + " removed:" + items)
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)


def remove2(update, context):
    
    #working variables
    currentList = []
    removedList = []
    items = ""
    
    #tries to open the list file
    try:
        file = open("./lists/" + str(update.effective_chat.id) + "-2", "rb")
    except: #throws an error if there is no file
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Your currently do not have a list 2 to remove from.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    currentList = pickle.load(file)
    file.close()

    #splits message String
    message = update.message.text.split()
    
    #throws an error if there is no specification what to remove
    if len(message) == 1:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ To remove an entry from list 2 enter a number after the '/remove2' command. To remove all previously drawn entries use '/remove2 drawn'.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    
    #checks if the specifier is 'drawn', if not it throws an error
    if not message[1]=="drawn":
        if not is_number(message[1]):
            context.bot.send_message(chat_id=update.effective_chat.id, text="❌ To remove an entry from list 2 enter a number after the '/remove2' command. To remove all previously drawn entries use '/remove2 drawn'.")
            return
        
    #checks if the specifier is a number
    if is_number(message[1]):
        
        #throws an error if the specifier exceeds the list lenght
        if int(message[1]) > len(currentList):
            context.bot.send_message(chat_id=update.effective_chat.id, text="❌ There is no item number " + message[1] + " in your list 2.")
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
            return
        
        #keeps entry in woking wariable
        items = currentList[int(message[1])-1]
		
		#deletes the entry from the working list
        del currentList[int(message[1])-1]
        
        #tries to open the drawn index
        try:
            file = open("./lists/" + str(update.effective_chat.id) + "-2" + "drawn", "rb")
            drawnList = pickle.load(file)
            file.close()
            
            #tries to remove the index from the drawn index
            try:
                drawnList.remove(int(message[1])-1)
            except:
                ()
            else:#saves the edited drawn index
                file = open("./lists/" + str(update.effective_chat.id) + "-2" + "drawn", "wb")
                pickle.dump(drawnList, file)
                file.close()
        except:
            ()
    
    #precedure to remove all drawn entries
    if message[1]=="drawn":
        	
		
        #checks if there is an list of drawn indexes
        try:
            file = open("./lists/" + str(update.effective_chat.id) + "-2" + "drawn", "rb")
        except:
            context.bot.send_message(chat_id=update.effective_chat.id, text="List 2 ❌ Your currently do not have any previously drawn entries.")
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
            return
        drawnList = pickle.load(file)
        file.close()
        
        #loops throught the drawn indexes and apends the message
        for i in range(len(drawnList)):
            items += "\n" + str(drawnList[i] + 1) + ": " + currentList[drawnList[i]]
			
	    #keeps track of which entries were removed
            removedList.append(drawnList[i])
			
	    #breaks list appending when max message length is near and informs user
            if len(items)> 3584:
                items += "\nList 2 ❌ You have to many drawn entries. Only removing the first " + str(i + 1)
                break
			
	#sorts drawn List in decending order to only delete correct entries
        removedList.sort(reverse = True)
	
	#loops throught the drawn indexes and removes the entries
        for i in range(len(removedList)):
		
	    #removes all removed entries from the list
            del currentList[removedList[i]]
		
	    #removes all removed entries from the drawn list
            drawnList.remove(removedList[i])
		
        #saves the empty list
        file = open("./lists/" + str(update.effective_chat.id) + "-2" + "drawn", "wb")
        pickle.dump(drawnList, file)
        file.close()
        
        #detetes any old drawn list
        try:
            os.remove("./lists/" + str(update.effective_chat.id) + "-2" + "drawn_old")
        except:
            ()
            
        #archives the emptied list
        os.rename("./lists/" + str(update.effective_chat.id) + "-2" + "drawn" , "./lists/" + str(update.effective_chat.id) + "-2" + "drawn_old")
    
    #saves the shortened working list to the list file
    file = open("./lists/" + str(update.effective_chat.id) + "-2" , "wb")
    pickle.dump(currentList, file)
    file.close()
    
    #sends the message for specific entry removal
    if is_number(message[1]):
        context.bot.send_message(chat_id=update.effective_chat.id, text="List 2 ✅ " + update.effective_user.first_name + " removed " + message[1] + ": '" + items + "'")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
    
    #sends the message for drawn entry
    if message[1]=="drawn":
        context.bot.send_message(chat_id=update.effective_chat.id, text="List 2 ✅ " + update.effective_user.first_name + " removed:" + items)
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)


def remove3(update, context):
    
    #working variables
    currentList = []
    removedList = []
    items = ""
    
    #tries to open the list file
    try:
        file = open("./lists/" + str(update.effective_chat.id) + "-3", "rb")
    except: #throws an error if there is no file
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Your currently do not have a list 3 to remove from.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    currentList = pickle.load(file)
    file.close()

    #splits message String
    message = update.message.text.split()
    
    #throws an error if there is no specification what to remove
    if len(message) == 1:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ To remove an entry from list 3 enter a number after the '/remove3' command. To remove all previously drawn entries use '/remove3 drawn'.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    
    #checks if the specifier is 'drawn', if not it throws an error
    if not message[1]=="drawn":
        if not is_number(message[1]):
            context.bot.send_message(chat_id=update.effective_chat.id, text="❌ To remove an entry from list 3 enter a number after the '/remove3' command. To remove all previously drawn entries use '/remove3 drawn'.")
            return
        
    #checks if the specifier is a number
    if is_number(message[1]):
        
        #throws an error if the specifier exceeds the list lenght
        if int(message[1]) > len(currentList):
            context.bot.send_message(chat_id=update.effective_chat.id, text="❌ There is no item number " + message[1] + " in your list 3.")
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
            return
        
        #keeps entry in woking wariable
        items = currentList[int(message[1])-1]
		
		#deletes the entry from the working list
        del currentList[int(message[1])-1]
        
        #tries to open the drawn index
        try:
            file = open("./lists/" + str(update.effective_chat.id) + "-3" + "drawn", "rb")
            drawnList = pickle.load(file)
            file.close()
            
            #tries to remove the index from the drawn index
            try:
                drawnList.remove(int(message[1])-1)
            except:
                ()
            else:#saves the edited drawn index
                file = open("./lists/" + str(update.effective_chat.id) + "-3" + "drawn", "wb")
                pickle.dump(drawnList, file)
                file.close()
        except:
            ()
    
    #precedure to remove all drawn entries
    if message[1]=="drawn":
        	
		
        #checks if there is an list of drawn indexes
        try:
            file = open("./lists/" + str(update.effective_chat.id) + "-3" + "drawn", "rb")
        except:
            context.bot.send_message(chat_id=update.effective_chat.id, text="List 3 ❌ Your currently do not have any previously drawn entries.")
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
            return
        drawnList = pickle.load(file)
        file.close()
        
        #loops throught the drawn indexes and apends the message
        for i in range(len(drawnList)):
            items += "\n" + str(drawnList[i] + 1) + ": " + currentList[drawnList[i]]
			
	    #keeps track of which entries were removed
            removedList.append(drawnList[i])
			
	    #breaks list appending when max message length is near and informs user
            if len(items)> 3584:
                items += "\nList 3 ❌ You have to many drawn entries. Only removing the first " + str(i + 1)
                break
			
	#sorts drawn List in decending order to only delete correct entries
        removedList.sort(reverse = True)
	
	#loops throught the drawn indexes and removes the entries
        for i in range(len(removedList)):
		
	    #removes all removed entries from the list
            del currentList[removedList[i]]
		
	    #removes all removed entries from the drawn list
            drawnList.remove(removedList[i])
		
        #saves the empty list
        file = open("./lists/" + str(update.effective_chat.id) + "-3" + "drawn", "wb")
        pickle.dump(drawnList, file)
        file.close()
        
        #detetes any old drawn list
        try:
            os.remove("./lists/" + str(update.effective_chat.id) + "-3" + "drawn_old")
        except:
            ()
            
        #archives the emptied list
        os.rename("./lists/" + str(update.effective_chat.id) + "-3" + "drawn" , "./lists/" + str(update.effective_chat.id) + "-3" + "drawn_old")
    
    #saves the shortened working list to the list file
    file = open("./lists/" + str(update.effective_chat.id) + "-3" , "wb")
    pickle.dump(currentList, file)
    file.close()
    
    #sends the message for specific entry removal
    if is_number(message[1]):
        context.bot.send_message(chat_id=update.effective_chat.id, text="List 3 ✅ " + update.effective_user.first_name + " removed " + message[1] + ": '" + items + "'")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
    
    #sends the message for drawn entry
    if message[1]=="drawn":
        context.bot.send_message(chat_id=update.effective_chat.id, text="List 3 ✅ " + update.effective_user.first_name + " removed:" + items)
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)



#changes a list entry
def edit(update, context):
    
    #working variables
    currentList = []
    
    #check if list file exist and if so load it
    try:
        file = open("./lists/" + str(update.effective_chat.id), "rb")
    except:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Your currently do not have a list to edit a message from.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return 
    currentList = pickle.load(file)
    file.close()

    #splits message String
    message = update.message.text.split()
    
    #error message for missing parameters
    if len(message) <= 2:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Please send the number of the item you want to edit after the '/edit' command, followed by your new item.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    
    #error message for wrong parameter
    if not is_number(message[1]):
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ To edit an entry on the list enter a number after the '/edit' command.")
        return
    
    #error message for out of list parameter
    if int(message[1])-1 == len(currentList):
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ There is no item number " + message[1] + " in your list.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    
    #saves old message and replaces it with new one
    pos = int(message[1])-1
    old = currentList[pos]
    del message[0:2]
    currentList[pos]=(' '.join(message))
    
    #saves the canged list file
    file = open("./lists/" + str(update.effective_chat.id), "wb")
    pickle.dump(currentList, file)
    file.close()
    
    #sends confirmation
    context.bot.send_message(chat_id=update.effective_chat.id, text="✅ " + update.effective_user.first_name + " changed " + str(pos +1) + " from '" + old + "' to '" + ' '.join(message) + "'")
    context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)


def edit2(update, context):
    
    #working variables
    currentList = []
    
    #check if list file exist and if so load it
    try:
        file = open("./lists/" + str(update.effective_chat.id) + "-2", "rb")
    except:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Your currently do not have a list 2 to edit a message from.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return 
    currentList = pickle.load(file)
    file.close()

    #splits message String
    message = update.message.text.split()
    
    #error message for missing parameters
    if len(message) <= 2:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Please send the number of the item you want to edit after the '/edit2' command, followed by your new item.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    
    #error message for wrong parameter
    if not is_number(message[1]):
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ To edit an entry on the list enter a number after the '/edit2' command.")
        return
    
    #error message for out of list parameter
    if int(message[1])-1 == len(currentList):
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ There is no item number " + message[1] + " in your list 2.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    
    #saves old message and replaces it with new one
    pos = int(message[1])-1
    old = currentList[pos]
    del message[0:2]
    currentList[pos]=(' '.join(message))
    
    #saves the canged list file
    file = open("./lists/" + str(update.effective_chat.id) + "-2", "wb")
    pickle.dump(currentList, file)
    file.close()
    
    #sends confirmation
    context.bot.send_message(chat_id=update.effective_chat.id, text="List 2 ✅ " + update.effective_user.first_name + " changed " + str(pos +1) + " from '" + old + "' to '" + ' '.join(message) + "'")
    context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)


def edit3(update, context):
    
    #working variables
    currentList = []
    
    #check if list file exist and if so load it
    try:
        file = open("./lists/" + str(update.effective_chat.id) + "-3", "rb")
    except:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Your currently do not have a list 3 to edit a message from.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return 
    currentList = pickle.load(file)
    file.close()

    #splits message String
    message = update.message.text.split()
    
    #error message for missing parameters
    if len(message) <= 2:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Please send the number of the item you want to edit after the '/edit3' command, followed by your new item.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    
    #error message for wrong parameter
    if not is_number(message[1]):
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ To edit an entry on the list enter a number after the '/edit3' command.")
        return
    
    #error message for out of list parameter
    if int(message[1])-1 == len(currentList):
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ There is no item number " + message[1] + " in your list 3.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    
    #saves old message and replaces it with new one
    pos = int(message[1])-1
    old = currentList[pos]
    del message[0:2]
    currentList[pos]=(' '.join(message))
    
    #saves the canged list file
    file = open("./lists/" + str(update.effective_chat.id) + "-3", "wb")
    pickle.dump(currentList, file)
    file.close()
    
    #sends confirmation
    context.bot.send_message(chat_id=update.effective_chat.id, text="List 3 ✅ " + update.effective_user.first_name + " changed " + str(pos +1) + " from '" + old + "' to '" + ' '.join(message) + "'")
    context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)



#recalles the entire list or just the drawn subset
def showList(update, context):
    
    #working variables
    currentList = []
    position = 1
    endPointer = 0
    drawnList = []
    
    #check if list file exist and if so load it
    try:
        file = open("./lists/" + str(update.effective_chat.id), "rb")
    except:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Your currently do not have a list to show.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    currentList = pickle.load(file)
    file.close()
    
    #splits message
    message = update.message.text.split()
    
    #checks if message length is longer than 1
    if not len(message) == 1:
        
        #checks if second word is number
        if not is_number(message[1]):
            
            #checks if second word is "drawn"
            if message[1] == "drawn":
                
                #check if drawn list file exist and if so load it
                try:
                    file = open("./lists/" + str(update.effective_chat.id) + "drawn", "rb")
                except:
                    context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Your currently do not have any previously drawn entries")
                    context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
                    return
                drawnList = pickle.load(file)
                file.close()
                
                #creates string for drawn list return
                strList = "✅ " + update.effective_user.first_name + ", here are your drawn entries:"
                
                #error if there are no drawn entries
                if len(drawnList) == 0:
                    context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Your currently do not have any previously drawn entries")
                    context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
                    return
                
                #appends the message String by drawn entries
                for i in range(len(drawnList)):
                    
                    strList += "\n" + str(drawnList[i] + 1) + ": " + currentList[drawnList[i]]
                    
                    #breaks list appending when max message length is near and informs user
                    if len(strList)> 3584:
                        strList += "\n❌ You have to many drawn entries. Only displaying the first " + str(i + 1)
                        break

                #sends out message
                context.bot.send_message(chat_id=update.effective_chat.id, text=strList)
                context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
                return

            #error if there is not a number or "drawn" after the "/list"
            context.bot.send_message(chat_id=update.effective_chat.id, text="❌ To call a specific section of the list enter a number after the '/list' command or use '/list drawn' to show all previously drawn items.")
            return

        #saves the send number th the working variable
        position = int(message[1])

    #creates the message string
    strList = "✅ " + update.effective_user.first_name + ", here are entries " + str(position) + " through {} of " + str(len(currentList)) + ":"

    #decrements the position to become consistent with the array index
    position -= 1

    #loops the list entries into the message
    for i in range(position, len(currentList)):  
        strList += "\n" + str(i + 1) + ": " + currentList[i]
        endPointer = i + 1

        #break if message is about to exceed max message length
        if len(strList)> 3584:
            strList += "\nThe list is not over yet. Use '/list " + str(i + 2) + "' to continue."
            break

    #send message
    context.bot.send_message(chat_id=update.effective_chat.id, text=strList.format(endPointer))
    context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)


def showList2(update, context):
    
    #working variables
    currentList = []
    position = 1
    endPointer = 0
    drawnList = []
    
    #check if list file exist and if so load it
    try:
        file = open("./lists/" + str(update.effective_chat.id) + "-2", "rb")
    except:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Your currently do not have a list 2 to show.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    currentList = pickle.load(file)
    file.close()
    
    #splits message
    message = update.message.text.split()
    
    #checks if message length is longer than 1
    if not len(message) == 1:
        
        #checks if second word is number
        if not is_number(message[1]):
            
            #checks if second word is "drawn"
            if message[1] == "drawn":
                
                #check if drawn list file exist and if so load it
                try:
                    file = open("./lists/" + str(update.effective_chat.id) + "-2" + "drawn", "rb")
                except:
                    context.bot.send_message(chat_id=update.effective_chat.id, text="List 2 ❌ Your currently do not have any previously drawn entries")
                    context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
                    return
                drawnList = pickle.load(file)
                file.close()
                
                #creates string for drawn list return
                strList = "List 2 ✅ " + update.effective_user.first_name + ", here are your drawn entries:"
                
                #error if there are no drawn entries
                if len(drawnList) == 0:
                    context.bot.send_message(chat_id=update.effective_chat.id, text="List 2 ❌ Your currently do not have any previously drawn entries")
                    context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
                    return
                
                #appends the message String by drawn entries
                for i in range(len(drawnList)):
                    
                    strList += "\n" + str(drawnList[i] + 1) + ": " + currentList[drawnList[i]]
                    
                    #breaks list appending when max message length is near and informs user
                    if len(strList)> 3584:
                        strList += "\nList 2 ❌ You have to many drawn entries. Only displaying the first " + str(i + 1)
                        break

                #sends out message
                context.bot.send_message(chat_id=update.effective_chat.id, text=strList)
                context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
                return

            #error if there is not a number or "drawn" after the "/list"
            context.bot.send_message(chat_id=update.effective_chat.id, text="❌ To call a specific section of list 2 enter a number after the '/list2' command or use '/list2 drawn' to show all previously drawn items.")
            return

        #saves the send number th the working variable
        position = int(message[1])

    #creates the message string
    strList = "List 2 ✅ " + update.effective_user.first_name + ", here are entries " + str(position) + " through {} of " + str(len(currentList)) + ":"

    #decrements the position to become consistent with the array index
    position -= 1

    #loops the list entries into the message
    for i in range(position, len(currentList)):  
        strList += "\n" + str(i + 1) + ": " + currentList[i]
        endPointer = i + 1

        #break if message is about to exceed max message length
        if len(strList)> 3584:
            strList += "\nList 2 is not over yet. Use '/list2 " + str(i + 2) + "' to continue."
            break

    #send message
    context.bot.send_message(chat_id=update.effective_chat.id, text=strList.format(endPointer))
    context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)


def showList3(update, context):
    
    #working variables
    currentList = []
    position = 1
    endPointer = 0
    drawnList = []
    
    #check if list file exist and if so load it
    try:
        file = open("./lists/" + str(update.effective_chat.id) + "-3", "rb")
    except:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Your currently do not have a list 3 to show.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    currentList = pickle.load(file)
    file.close()
    
    #splits message
    message = update.message.text.split()
    
    #checks if message length is longer than 1
    if not len(message) == 1:
        
        #checks if second word is number
        if not is_number(message[1]):
            
            #checks if second word is "drawn"
            if message[1] == "drawn":
                
                #check if drawn list file exist and if so load it
                try:
                    file = open("./lists/" + str(update.effective_chat.id) + "-3" + "drawn", "rb")
                except:
                    context.bot.send_message(chat_id=update.effective_chat.id, text="List 3 ❌ Your currently do not have any previously drawn entries")
                    context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
                    return
                drawnList = pickle.load(file)
                file.close()
                
                #creates string for drawn list return
                strList = "List 3 ✅ " + update.effective_user.first_name + ", here are your drawn entries:"
                
                #error if there are no drawn entries
                if len(drawnList) == 0:
                    context.bot.send_message(chat_id=update.effective_chat.id, text="List 3 ❌ Your currently do not have any previously drawn entries")
                    context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
                    return
                
                #appends the message String by drawn entries
                for i in range(len(drawnList)):
                    
                    strList += "\n" + str(drawnList[i] + 1) + ": " + currentList[drawnList[i]]
                    
                    #breaks list appending when max message length is near and informs user
                    if len(strList)> 3584:
                        strList += "\nList 3 ❌ You have to many drawn entries. Only displaying the first " + str(i + 1)
                        break

                #sends out message
                context.bot.send_message(chat_id=update.effective_chat.id, text=strList)
                context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
                return

            #error if there is not a number or "drawn" after the "/list"
            context.bot.send_message(chat_id=update.effective_chat.id, text="❌ To call a specific section of list 3 enter a number after the '/list3' command or use '/list3 drawn' to show all previously drawn items.")
            return

        #saves the send number th the working variable
        position = int(message[1])

    #creates the message string
    strList = "List 3 ✅ " + update.effective_user.first_name + ", here are entries " + str(position) + " through {} of " + str(len(currentList)) + ":"

    #decrements the position to become consistent with the array index
    position -= 1

    #loops the list entries into the message
    for i in range(position, len(currentList)):  
        strList += "\n" + str(i + 1) + ": " + currentList[i]
        endPointer = i + 1

        #break if message is about to exceed max message length
        if len(strList)> 3584:
            strList += "\nList 3 is not over yet. Use '/list3 " + str(i + 2) + "' to continue."
            break

    #send message
    context.bot.send_message(chat_id=update.effective_chat.id, text=strList.format(endPointer))
    context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)



#recalles a random entrie from the list
def draw(update, context):
    
    #working variables
    currentList = []
    drawnList = []
    number = 1

    #checks if there is a list and loads it
    try:
        file = open("./lists/" + str(update.effective_chat.id), "rb")
    except:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Your currently do not have a list to draw from.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    currentList = pickle.load(file)
    file.close()

    #checks if there is an list of drawn indexes
    try:
        file = open("./lists/" + str(update.effective_chat.id) + "drawn", "rb")
    except:
        ()
    else:
        drawnList = pickle.load(file)
        file.close()

    #splits messaage String
    message = update.message.text.split()

    #check for message length
    if not len(message) == 1:

        #error if 2nd word is not number
        if not is_number(message[1]):
            context.bot.send_message(chat_id=update.effective_chat.id, text="❌ To draw more than one item from the list enter a number after the '/draw' command.")
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
            return

        #sets the working variable to the number from the message
        number = int(message[1])

    #creates the message
    strList = "✅ " + update.effective_user.first_name + " drew the following:"
    
    #loops the number of items to draw
    for i in range(number):

        #picks a random item
        position = randint(0, len(currentList) - 1)
        
        #extracts item from list
        item = currentList[position]
        
        #adds item to message
        strList += "\n" + str(position + 1) + ": " + item

        #add the drawn entries index to the drawn list
        if not position in drawnList:
            drawnList.append(position)
        
        #break if message about to get to long
        if len(strList)> 3584:
            strList += "\n❌ You tried to draw to many entries. Only " + str(i + 1) + " were drawn."
            break
    
    #saves the drawn list
    file = open("./lists/" + str(update.effective_chat.id) + "drawn", "wb")
    pickle.dump(drawnList, file)
    file.close()
    
    #sends message
    context.bot.send_message(chat_id=update.effective_chat.id, text=strList)
    context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)


def draw2(update, context):
    
    #working variables
    currentList = []
    drawnList = []
    number = 1

    #checks if there is a list and loads it
    try:
        file = open("./lists/" + str(update.effective_chat.id) + "-2", "rb")
    except:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Your currently do not have a list 2 to draw from.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    currentList = pickle.load(file)
    file.close()

    #checks if there is an list of drawn indexes
    try:
        file = open("./lists/" + str(update.effective_chat.id) + "-2" + "drawn", "rb")
    except:
        ()
    else:
        drawnList = pickle.load(file)
        file.close()

    #splits messaage String
    message = update.message.text.split()

    #check for message length
    if not len(message) == 1:

        #error if 2nd word is not number
        if not is_number(message[1]):
            context.bot.send_message(chat_id=update.effective_chat.id, text="❌ To draw more than one item from list 2 enter a number after the '/draw2' command.")
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
            return

        #sets the working variable to the number from the message
        number = int(message[1])

    #creates the message
    strList = "List 2 ✅ " + update.effective_user.first_name + " drew the following:"
    
    #loops the number of items to draw
    for i in range(number):

        #picks a random item
        position = randint(0, len(currentList) - 1)
        
        #extracts item from list
        item = currentList[position]
        
        #adds item to message
        strList += "\n" + str(position + 1) + ": " + item

        #add the drawn entries index to the drawn list
        if not position in drawnList:
            drawnList.append(position)
        
        #break if message about to get to long
        if len(strList)> 3584:
            strList += "\nList 2 ❌ You tried to draw to many entries. Only " + str(i + 1) + " were drawn."
            break
    
    #saves the drawn list
    file = open("./lists/" + str(update.effective_chat.id) + "-2" + "drawn", "wb")
    pickle.dump(drawnList, file)
    file.close()
    
    #sends message
    context.bot.send_message(chat_id=update.effective_chat.id, text=strList)
    context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)


def draw3(update, context):
    
    #working variables
    currentList = []
    drawnList = []
    number = 1

    #checks if there is a list and loads it
    try:
        file = open("./lists/" + str(update.effective_chat.id) + "-3", "rb")
    except:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Your currently do not have a list 3 to draw from.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    currentList = pickle.load(file)
    file.close()

    #checks if there is an list of drawn indexes
    try:
        file = open("./lists/" + str(update.effective_chat.id) + "-3" + "drawn", "rb")
    except:
        ()
    else:
        drawnList = pickle.load(file)
        file.close()

    #splits messaage String
    message = update.message.text.split()

    #check for message length
    if not len(message) == 1:

        #error if 2nd word is not number
        if not is_number(message[1]):
            context.bot.send_message(chat_id=update.effective_chat.id, text="❌ To draw more than one item from list 3 enter a number after the '/draw3' command.")
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
            return

        #sets the working variable to the number from the message
        number = int(message[1])

    #creates the message
    strList = "List 3 ✅ " + update.effective_user.first_name + " drew the following:"
    
    #loops the number of items to draw
    for i in range(number):

        #picks a random item
        position = randint(0, len(currentList) - 1)
        
        #extracts item from list
        item = currentList[position]
        
        #adds item to message
        strList += "\n" + str(position + 1) + ": " + item

        #add the drawn entries index to the drawn list
        if not position in drawnList:
            drawnList.append(position)
        
        #break if message about to get to long
        if len(strList)> 3584:
            strList += "\nList 3 ❌ You tried to draw to many entries. Only " + str(i + 1) + " were drawn."
            break
    
    #saves the drawn list
    file = open("./lists/" + str(update.effective_chat.id) + "-3" + "drawn", "wb")
    pickle.dump(drawnList, file)
    file.close()
    
    #sends message
    context.bot.send_message(chat_id=update.effective_chat.id, text=strList)
    context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)



#removes entry from the drawn list or resets the drawn list
def undraw(update, context):
	
    #working variables
    drawnList = []
    currentList = []
    strList = "✅ " + update.effective_user.first_name + " undrew"
	
    #check if drawn list file exist and if so load it
    try:
        file = open("./lists/" + str(update.effective_chat.id) + "drawn", "rb")
    except:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Your currently do not have any previously drawn entries")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    drawnList = pickle.load(file)
    file.close()
	
    #checks if there is a list and loads it
    try:
        file = open("./lists/" + str(update.effective_chat.id), "rb")
    except:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Your currently do not have a list.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    currentList = pickle.load(file)
    file.close()
	
    #splits message String
    message = update.message.text.split()
	
    #throws an error if there is no specification what to remove
    if len(message) == 1:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Undraw an entry enter its number after the '/undraw' command. To undraw all previously drawn entries use '/undraw all'.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
	
    #checks for "all" in message
    if not message[1] == "all":
            
        #checks for number
        if not is_number(message[1]):
            context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Undraw an entry enter its number after the '/undraw' command. To undraw all previously drawn entries use '/undraw all'.")
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
            return
           
        #error if there are no drawn entries
        if len(drawnList) == 0:
            context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Your currently do not have any previously drawn entries")
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
            return

        #is number:
        try:

            #removes drawn marker
            drawnList.remove(int(message[1]) - 1)
	    	
        except:
			
            #error message if not drawn
            context.bot.send_message(chat_id=update.effective_chat.id, text="❌ " + message[1] + " was not drawn. No change required.")
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
            return
			
        else:
    		
            #success message
            strList += " " + message[1] + ": '" + currentList[int(message[1]) - 1] + "'"
	    
    else:
		
         #loops the number of items to draw
         for i in range(len(drawnList)):
			
            #adds item to message
            strList += "\n" + str(drawnList[0] + 1) + ": " + currentList[drawnList[0]]
			
            #removes entry from list
            drawnList.pop(0)
						
            #break if message about to get to long
            if len(strList)> 3584:
                strList += "\n❌ You have drawn to many entries. Only " + str(i + 1) + " were undrawn."
                break
		
    #removes old backup file
    try:
        os.remove("./lists/" + str(update.effective_chat.id) + "drawn_old")
    except:
        ()
	
    #backup of current file
    os.rename("./lists/" + str(update.effective_chat.id) + "drawn" , "./lists/" + str(update.effective_chat.id) + "drawn_old")

    #saves the drawn list
    file = open("./lists/" + str(update.effective_chat.id) + "drawn", "wb")
    pickle.dump(drawnList, file)
    file.close()
	
    #sends out message
    context.bot.send_message(chat_id=update.effective_chat.id, text=strList)
    context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)


def undraw2(update, context):
	
    #working variables
    drawnList = []
    currentList = []
    strList = "List 2 ✅ " + update.effective_user.first_name + " undrew"
	
    #check if drawn list file exist and if so load it
    try:
        file = open("./lists/" + str(update.effective_chat.id) + "-2" + "drawn", "rb")
    except:
        context.bot.send_message(chat_id=update.effective_chat.id, text="List 2 ❌ Your currently do not have any previously drawn entries")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    drawnList = pickle.load(file)
    file.close()
	
    #checks if there is a list and loads it
    try:
        file = open("./lists/" + str(update.effective_chat.id) + "-2", "rb")
    except:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Your currently do not have a list 2.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    currentList = pickle.load(file)
    file.close()
	
    #splits message String
    message = update.message.text.split()
	
    #throws an error if there is no specification what to remove
    if len(message) == 1:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Undraw an entry enter its number after the '/undraw2' command. To undraw all previously drawn entries use '/undraw2 all'.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
	
    #checks for "all" in message
    if not message[1] == "all":
            
        #checks for number
        if not is_number(message[1]):
            context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Undraw an entry enter its number after the '/undraw' command. To undraw all previously drawn entries use '/undraw all'.")
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
            return
           
        #error if there are no drawn entries
        if len(drawnList) == 0:
            context.bot.send_message(chat_id=update.effective_chat.id, text="List 2 ❌ Your currently do not have any previously drawn entries")
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
            return

        #is number:
        try:

            #removes drawn marker
            drawnList.remove(int(message[1]) - 1)
	    	
        except:
			
            #error message if not drawn
            context.bot.send_message(chat_id=update.effective_chat.id, text="List 2 ❌ " + message[1] + " was not drawn. No change required.")
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
            return
			
        else:
    		
            #success message
            strList += " " + message[1] + ": '" + currentList[int(message[1]) - 1] + "'"
	    
    else:
		
         #loops the number of items to draw
         for i in range(len(drawnList)):
			
            #adds item to message
            strList += "\n" + str(drawnList[0] + 1) + ": " + currentList[drawnList[0]]
			
            #removes entry from list
            drawnList.pop(0)
						
            #break if message about to get to long
            if len(strList)> 3584:
                strList += "\nList 2 ❌ You have drawn to many entries. Only " + str(i + 1) + " were undrawn."
                break
		
    #removes old backup file
    try:
        os.remove("./lists/" + str(update.effective_chat.id) + "-2" + "drawn_old")
    except:
        ()
	
    #backup of current file
    os.rename("./lists/" + str(update.effective_chat.id) + "-2" + "drawn" , "./lists/" + str(update.effective_chat.id) + "-2" + "drawn_old")

    #saves the drawn list
    file = open("./lists/" + str(update.effective_chat.id) + "-2" + "drawn", "wb")
    pickle.dump(drawnList, file)
    file.close()
	
    #sends out message
    context.bot.send_message(chat_id=update.effective_chat.id, text=strList)
    context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)


def undraw3(update, context):
	
    #working variables
    drawnList = []
    currentList = []
    strList = "List 3 ✅ " + update.effective_user.first_name + " undrew"
	
    #check if drawn list file exist and if so load it
    try:
        file = open("./lists/" + str(update.effective_chat.id) + "-3" + "drawn", "rb")
    except:
        context.bot.send_message(chat_id=update.effective_chat.id, text="List 3 ❌ Your currently do not have any previously drawn entries")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    drawnList = pickle.load(file)
    file.close()
	
    #checks if there is a list and loads it
    try:
        file = open("./lists/" + str(update.effective_chat.id) + "-3", "rb")
    except:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Your currently do not have a list 3.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    currentList = pickle.load(file)
    file.close()
	
    #splits message String
    message = update.message.text.split()
	
    #throws an error if there is no specification what to remove
    if len(message) == 1:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Undraw an entry enter its number after the '/undraw3' command. To undraw all previously drawn entries use '/undraw3 all'.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
	
    #checks for "all" in message
    if not message[1] == "all":
            
        #checks for number
        if not is_number(message[1]):
            context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Undraw an entry enter its number after the '/undraw' command. To undraw all previously drawn entries use '/undraw all'.")
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
            return
           
        #error if there are no drawn entries
        if len(drawnList) == 0:
            context.bot.send_message(chat_id=update.effective_chat.id, text="List 3 ❌ Your currently do not have any previously drawn entries")
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
            return

        #is number:
        try:

            #removes drawn marker
            drawnList.remove(int(message[1]) - 1)
	    	
        except:
			
            #error message if not drawn
            context.bot.send_message(chat_id=update.effective_chat.id, text="List 3 ❌ " + message[1] + " was not drawn. No change required.")
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
            return
			
        else:
    		
            #success message
            strList += " " + message[1] + ": '" + currentList[int(message[1]) - 1] + "'"
	    
    else:
		
         #loops the number of items to draw
         for i in range(len(drawnList)):
			
            #adds item to message
            strList += "\n" + str(drawnList[0] + 1) + ": " + currentList[drawnList[0]]
			
            #removes entry from list
            drawnList.pop(0)
						
            #break if message about to get to long
            if len(strList)> 3584:
                strList += "\nList 3 ❌ You have drawn to many entries. Only " + str(i + 1) + " were undrawn."
                break
		
    #removes old backup file
    try:
        os.remove("./lists/" + str(update.effective_chat.id) + "-3" + "drawn_old")
    except:
        ()
	
    #backup of current file
    os.rename("./lists/" + str(update.effective_chat.id) + "-3" + "drawn" , "./lists/" + str(update.effective_chat.id) + "-3" + "drawn_old")

    #saves the drawn list
    file = open("./lists/" + str(update.effective_chat.id) + "-3" + "drawn", "wb")
    pickle.dump(drawnList, file)
    file.close()
	
    #sends out message
    context.bot.send_message(chat_id=update.effective_chat.id, text=strList)
    context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)



#archives the current list and ist drawn counterpart by replacing the old archive file
def reset(update, context):
    
    #checks for list to delete
    if not os.path.exists("./lists/" + str(update.effective_chat.id)):
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Your currently do not have a list to delete.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    
    #splits message String
    message = update.message.text.split()
    
    #request for confirmation
    if len(message) == 1:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Please send me the phrase 'I want to delete my current list.' after /reset to delete your current list.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    
    #check for correct confirmation text
    if update.message.text == "/reset I want to delete my current list.":
		
	#removes old backups
        try:
            os.remove("./lists/" + str(update.effective_chat.id) + "_old")
        except:
            ()
        try:
            os.remove("./lists/" + str(update.effective_chat.id) + "drawn_old")
        except:
            ()
        
        #creates new backups
        os.rename("./lists/" + str(update.effective_chat.id) , "./lists/" + str(update.effective_chat.id) + "_old")
        try:
            os.rename("./lists/" + str(update.effective_chat.id) + "drawn" , "./lists/" + str(update.effective_chat.id) + "drawn_old")
        except:
            ()
		
        #confirmation message
        context.bot.send_message(chat_id=update.effective_chat.id, text="✅ Your list was deleted succesfully.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)


def reset2(update, context):
    
    #checks for list to delete
    if not os.path.exists("./lists/" + str(update.effective_chat.id) + "-2"):
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Your currently do not have a list 2 to delete.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    
    #splits message String
    message = update.message.text.split()
    
    #request for confirmation
    if len(message) == 1:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Please send me the phrase 'I want to delete my current list 2.' after /reset2 to delete your current list 2.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    
    #check for correct confirmation text
    if update.message.text == "/reset I want to delete my current list 2.":
		
	#removes old backups
        try:
            os.remove("./lists/" + str(update.effective_chat.id) + "-2" + "_old")
        except:
            ()
        try:
            os.remove("./lists/" + str(update.effective_chat.id) + "-2" + "drawn_old")
        except:
            ()
        
        #creates new backups
        os.rename("./lists/" + str(update.effective_chat.id) + "-2" , "./lists/" + str(update.effective_chat.id) + "-2" + "_old")
        try:
            os.rename("./lists/" + str(update.effective_chat.id) +"-2" + "drawn" , "./lists/" + str(update.effective_chat.id) + "-2" + "drawn_old")
        except:
            ()
		
        #confirmation message
        context.bot.send_message(chat_id=update.effective_chat.id, text="✅ Your list 2 was deleted succesfully.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)


def reset3(update, context):
    
    #checks for list to delete
    if not os.path.exists("./lists/" + str(update.effective_chat.id) + "-3"):
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Your currently do not have a list 3 to delete.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    
    #splits message String
    message = update.message.text.split()
    
    #request for confirmation
    if len(message) == 1:
        context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Please send me the phrase 'I want to delete my current list 3.' after /reset3 to delete your current list 3.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        return
    
    #check for correct confirmation text
    if update.message.text == "/reset I want to delete my current list 3.":
		
	#removes old backups
        try:
            os.remove("./lists/" + str(update.effective_chat.id) + "-3" + "_old")
        except:
            ()
        try:
            os.remove("./lists/" + str(update.effective_chat.id) + "-3" + "drawn_old")
        except:
            ()
        
        #creates new backups
        os.rename("./lists/" + str(update.effective_chat.id) + "-3" , "./lists/" + str(update.effective_chat.id) + "-3" + "_old")
        try:
            os.rename("./lists/" + str(update.effective_chat.id) +"-3" + "drawn" , "./lists/" + str(update.effective_chat.id) + "-3" + "drawn_old")
        except:
            ()
		
        #confirmation message
        context.bot.send_message(chat_id=update.effective_chat.id, text="✅ Your list 3 was deleted succesfully.")
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)



#returns the telegram user id
def getid(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text=str(update.effective_chat.id))
    context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)

    

def empty(update, context):
    
    #context.bot.send_message(chat_id=update.effective_chat.id, text='I do not know what to do.')
	return



def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)



def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater("123456789:an5idsmtz3o674jfnsu509ugu496heoghbq", use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("getid", getid))
	
    dp.add_handler(CommandHandler("add", add))
    dp.add_handler(CommandHandler("add2", add2))
    dp.add_handler(CommandHandler("add3", add3))
		
    dp.add_handler(CommandHandler("grupp", grupp))
    dp.add_handler(CommandHandler("grupp2", grupp2))
    dp.add_handler(CommandHandler("grupp3", grupp3))
	
    dp.add_handler(CommandHandler("remove", remove))
    dp.add_handler(CommandHandler("remove2", remove2))
    dp.add_handler(CommandHandler("remove3", remove3))
		
    dp.add_handler(CommandHandler("edit", edit))
    dp.add_handler(CommandHandler("edit2", edit2))
    dp.add_handler(CommandHandler("edit3", edit3))
	
    dp.add_handler(CommandHandler("list", showList))
    dp.add_handler(CommandHandler("list2", showList2))
    dp.add_handler(CommandHandler("list3", showList3))
	
    dp.add_handler(CommandHandler("draw", draw))
    dp.add_handler(CommandHandler("draw2", draw2))
    dp.add_handler(CommandHandler("draw3", draw3))
	
    dp.add_handler(CommandHandler("undraw", undraw))
    dp.add_handler(CommandHandler("undraw2", undraw2))
    dp.add_handler(CommandHandler("undraw3", undraw3))
	
    dp.add_handler(CommandHandler("reset", reset))
    dp.add_handler(CommandHandler("reset2", reset2))
    dp.add_handler(CommandHandler("reset3", reset3))


    # on noncommand i.e message - echo the message on Telegram
    #dp.add_handler(MessageHandler(Filters.text, empty))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()



if __name__ == '__main__':
    main()
