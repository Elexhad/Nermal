'''
Copyright 2021 Elex

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import sqlite3
import os, json

from datetime import datetime, timezone

config = {}
with open('config.json') as json_file:
    config = json.load(json_file)

dir = os.path.dirname(__file__)
db_file = os.path.join(dir, config['database_file_name'])


def initialize_database():
    """Define SQL tables and create them if they don't exist."""

    dailyChannelTable = """CREATE TABLE IF NOT EXISTS `daily_channel` (
                                `server_id` TEXT PRIMARY KEY,
                                `channel_id` TEXT
                                ); """

    tables = [dailyChannelTable]
    db = sqlite3.connect(db_file)
    for table in tables:
        db.execute(table)
    db.close()


def update_daily_channel(server_id, channel_id):
    db = sqlite3.connect(db_file)
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM daily_channel WHERE server_id=?''', (server_id,))
    data = cursor.fetchone()
    if data is not None:
        cursor.execute('''UPDATE daily_channel SET channel_id=? WHERE server_id=?''', (channel_id, server_id,))
    else:
        cursor.execute('''INSERT INTO daily_channel(server_id, channel_id) VALUES(?,?)''', (server_id, channel_id,))
    db.commit()
    db.close()

def remove_daily_channel(server_id):
    db = sqlite3.connect(db_file)
    cursor = db.cursor()
    cursor.execute('''DELETE FROM daily_channel WHERE server_id=?''', (server_id,))
    db.commit()
    db.close()

def check_daily_channel(server_id):
    db = sqlite3.connect(db_file)
    cursor = db.cursor()
    cursor.execute('''SELECT channel_id FROM daily_channel WHERE server_id=?''', (str(server_id),))
    channel = cursor.fetchone()
    db.close()
    if channel is not None:
        return int(channel[0])
    else:
        return False


def load_daily_channels():
    db = sqlite3.connect(db_file)
    cursor = db.cursor()
    cursor.execute('''SELECT channel_id FROM daily_channel''')
    channels = []
    for row in cursor:
        channels.append(row[0])
    db.close()
    return channels
