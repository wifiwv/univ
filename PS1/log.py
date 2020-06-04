import requests
import serial
import time
import threading
import json
from datetime import datetime
import tkinter as tk

# global config
API = "https://tonu.rocks/school/GreenHouse/api/"
preferences_endpoint = API + "preferences"
sensor = "DH11"
serial_port = '/dev/cu.wchusbserialfa130'  # (1)
baud_rate = 115200
today = datetime.now()
today = today.strftime("%b %d, %Y")
log_file = "Logs/log_" + today + ".txt"  # store logs locally as well
serial_connection = serial.Serial(serial_port, baud_rate, timeout=0.5)
time.sleep(1)  # give the connection a second to settle)
data = []

# user input variables
session_username = ''
session_password = ''


# GUI to get username and password
master = tk.Tk()
master.title('GreenHouse Login') 
tk.Label(master,
         text="Username").grid(row=0)
tk.Label(master,
         text="Password").grid(row=1)

# create entry inputs for username and password
username = tk.Entry(master)
password = tk.Entry(master)
password.config(show="*")
username.grid(row=0, column=1)
password.grid(row=1, column=1)


# get values from inputs
def show_entry_fields():
    global session_username, session_password, master
    session_username = username.get()
    session_password = password.get()
    print("Username: "+session_username)
    print("Password: "+session_password)
    master.destroy()

# submit form button
tk.Button(master, text='Submit',
          command=show_entry_fields).grid(row=3,
                                          column=1,
                                          sticky=tk.W,
                                          pady=4)
# keep GUI window open
tk.mainloop()

# default preferences
light = "200"
temperature = "25"
water = "40"
culture_id = "1"
config_msg = light + "e" + temperature + "e" + water + "ef"


# start a new session
session = requests.Session()
login_data = {'username': session_username, 'password': session_password}
login_response = session.post(API, json.dumps(login_data))

print(login_response.text)

# function to request preferences from the server


def updatePreferences():
    global light, temperature, water, culture_id, config_msg

    # get preferences from the server
    response = session.get(url=preferences_endpoint)

    # check if response status is ok
    if (response.status_code >= 400):
        print('\033[91m' + response.text + '\033[0m')
    else:
        # extract data in a json object
        preferences = response.json()

        # update preferences with remote ones
        for preference in preferences:
            if (preference['selected']):
                culture_id = str(preference['id'])
                light = str(preference['light'])
                temperature = str(preference['temperature'])
                water = str(preference['water'])

        # config message for Arduino
        config_msg = light + "e" + temperature + "e" + water + "ef"


# update config from preferences
updatePreferences()

# write configuration to serial
serial_connection.write(config_msg.encode())

# declare transfer message
line = '0_0_0'

# helper class to make asynchronous requests


class setInterval:
    def __init__(self, interval, action):
        self.interval = interval
        self.action = action
        self.stopEvent = threading.Event()
        thread = threading.Thread(target=self.__setInterval)
        thread.start()

    def __setInterval(self):
        nextTime = time.time() + self.interval
        while not self.stopEvent.wait(nextTime - time.time()):
            nextTime += self.interval
            self.action()

    def cancel(self):
        self.stopEvent.set()

# extract and handle log data from recieved message


def handleLogs():
    global data, light, temperature, water, culture_id, line

    # convert message to utf charset
    logs = line.decode("utf-8").strip()
    time_stamp = datetime.now().strftime("%H:%M:%S")

    # check if message is not empty
    if logs:

        # collect logs in data array and write them in a text file when it reeaches 10 logs
        if len(data) == 10:
            output_file = open(log_file, "a+")
            for record in data:
                output_file.write(record)
            data = []
            output_file.close()
        else:
            data.append(
                today + "/" + time_stamp + "_" + logs + "\n")

            # split message on logs' delimiter
            log = logs.split("_")
            # create string from log object
            log_object = json.dumps({
                "cultureId": culture_id,
                "light": log[0],
                "temperature": log[1],
                "water": log[2]
            })
            headers = {'Content-type': 'application/json'}

            # make PUT request and store response
            response = session.put(url=API + "logs/",
                                   data=log_object,
                                   headers=headers)

            # check response status and display its text
            if (response.status_code < 400):
                print('\033[94m' + response.text + '\033[0m')
            else:
                print('\033[91m' + response.text + '\033[0m')


# wait until Arduino is ready to communicate
state_msg = serial_connection.readline().decode("utf-8").strip()
if(state_msg == "Ready"):
    print("Connection settled")
    readRoutine = setInterval(3, handleLogs)


# update config message
    time.sleep(1)
    writeRoutine = setInterval(9, updatePreferences)

    # listen on serial to data from Arduino
    while 1:
        serial_connection.write(config_msg.encode())
        line = serial_connection.readline()
else:
    print(state_msg)

# t = threading.Timer(30, readRoutine.cancel)
# t.start()
