# !/usr/bin/env python3

try:
    from .tweetwatcher import Ui_MainWindow
except ImportError:
    from tweetwatcher import Ui_MainWindow
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QFileDialog
from PyQt5 import QtCore, QtGui, QtWidgets
from twitter import *
from time import sleep, time
from threading import Thread
from pandas import json_normalize
from pathlib import Path

import sqlite3
import pandas as pd
import json
import traceback

from os.path import isfile, getsize


def get_complete_text(df):
    fields = [i for i in
              ['retweeted_status.extended_tweet.full_text', 'retweeted_status.text', 'extended_tweet.full_text', 'text',
               'retweeted_status.quoted_status.full_text', 'retweeted_status.full_text', 'quoted_status.full_text',
               'full_text'] if i in df.columns]

    temp = df[fields[len(fields) - 1]]
    for i in range(len(fields) - 2, -1, -1):
        temp = df[fields[i]].fillna(temp)

    return temp


def write_file(df, table, format, part=0):
    part = "parte_" + str(part) + "_" if part > 0 else ''

    filename = table.replace('[', '').replace(']', '') + part + str(int(time())) + format
    if format == '.csv':
        df.to_csv(filename, index=False)
    elif format == '.xlsx':
        df.to_excel(filename, index=False, encoding='utf-8')


def get_credentials():
    home = str(Path.home())
    if isfile(home + '/credentials'):
        with open(home + '/credentials', 'r') as f:
            return [line.strip() for line in f.readlines()]
    else:
        return ['', '', '', '', '']


def is_sqlite3(filename):
    if not isfile(filename) or getsize(filename) < 100:
        return False

    with open(filename, 'rb') as fd:
        header = fd.read(100)

    return header[:16] == b'SQLite format 3\000'


def get_tables(database):
    conn = sqlite3.connect(database)
    cur = conn.cursor()
    tables = [name[0] for name in cur.execute("select name from sqlite_master where type='table';")]
    conn.close()
    return tables


class TextOutputWithSignal(QObject):
    received_text = pyqtSignal(str, name='receivedText')

    def __init__(self, text_edit_output):
        super().__init__()
        self.textEditOutput = text_edit_output


class Backend(Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.counter = 0
        self.stop_searching = False
        self.searching = False
        self.stop_exporting = False
        self.exporting = False

    def init_stuff(self):  # run after ui.setupUi()..
        self.textEditOutput = TextOutputWithSignal(self.textEditOutput)
        self.searchPushButtonSearch.clicked.connect(self.start_searching)
        self.searchPushButtonSearch.setDisabled(True)
        self.cancelPushButtonSearch.clicked.connect(self.set_stop_searching)
        self.cancelPushButtonSearch.setDisabled(True)

        self.textEditOutput.received_text.connect(self.append_text)
        self.pushButtonDatabasePathSearch.clicked.connect(self.select_file)
        self.pushButtonDatabasePathExport.clicked.connect(self.select_file_export)
        self.cancelPushButtonExport.clicked.connect(self.set_stop_exporting)
        self.cancelPushButtonExport.setDisabled(True)
        self.exportPushButtonExport.clicked.connect(self.start_exporting)
        self.exportPushButtonExport.setDisabled(True)

        token, token_secret, consumer_key, consumer_secret, database_path = get_credentials()
        self.lineAccessToken.setText(token)
        self.lineAccessTokenSecret.setText(token_secret)
        self.lineConsumerKey.setText(consumer_key)
        self.lineConsumerSecret.setText(consumer_secret)
        self.lineDatabasePathSearch.setText(database_path)

        self.lineSearchTerms.textChanged.connect(self.enable_disable_buttons)
        self.lineAccessToken.textChanged.connect(self.enable_disable_buttons)
        self.lineAccessTokenSecret.textChanged.connect(self.enable_disable_buttons)
        self.lineConsumerKey.textChanged.connect(self.enable_disable_buttons)
        self.lineConsumerSecret.textChanged.connect(self.enable_disable_buttons)
        self.lineDatabasePathSearch.textChanged.connect(self.enable_disable_buttons)
        self.lineDatabasePathExport.textChanged.connect(self.enable_disable_buttons)

        self.checkBoxAll.toggled.connect(self.lineEditLanguages.setDisabled)
        self.radioButtonSaveSingle.setChecked(True)
        self.radioButtonSaveSeparatedly.setDisabled(True)

        self.comboBoxSelectTable.currentIndexChanged.connect(self.set_since)
        self.dateTimeUntil.setDateTime(QtCore.QDateTime.fromSecsSinceEpoch(int(time())))

    def set_since(self):
        try:
            conn = sqlite3.connect(self.lineDatabasePathExport.text())
            since = pd.read_sql_query(
                'select timestamp from ' + '`{}`'.format(self.comboBoxSelectTable.currentText()) + 'limit 1',
                conn).timestamp[0]
            self.dateTimeSince.setDateTime(QtCore.QDateTime.fromSecsSinceEpoch(since))
            conn.close()
        except:
            print("Couldn't set since date.")

    def enable_disable_buttons(self):
        if len(self.lineSearchTerms.text()) \
                and len(self.lineAccessToken.text()) \
                and len(self.lineAccessTokenSecret.text()) \
                and len(self.lineConsumerKey.text()) \
                and len(self.lineConsumerSecret.text()) \
                and len(self.lineDatabasePathSearch.text()) \
                and (self.radioButtonSaveSingle.isChecked()
                     or self.radioButtonSaveSeparatedly.isChecked()
                     or self.radioButtonDontSave.isChecked()):

            self.searchPushButtonSearch.setDisabled(False)
        else:
            self.searchPushButtonSearch.setDisabled(True)

        if len(self.lineDatabasePathExport.text()) and is_sqlite3(self.lineDatabasePathExport.text()) \
                and not self.searching:
            self.comboBoxSelectTable.clear()
            self.comboBoxSelectTable.addItems(get_tables(self.lineDatabasePathExport.text()))
            self.exportPushButtonExport.setDisabled(False)
        else:
            self.exportPushButtonExport.setDisabled(True)
            self.comboBoxSelectTable.clear()

        if len(self.lineSearchTerms.text().split(',')) <= 1:
            self.radioButtonSaveSeparatedly.setDisabled(True)
        else:
            self.radioButtonSaveSeparatedly.setDisabled(False)

    def export(self):
        self.exportPushButtonExport.setText('Exporting...')
        self.exportPushButtonExport.setDisabled(True)
        self.cancelPushButtonExport.setDisabled(False)

        self.lineAccessToken.setDisabled(True)
        self.lineAccessTokenSecret.setDisabled(True)
        self.lineConsumerKey.setDisabled(True)
        self.lineConsumerSecret.setDisabled(True)
        self.lineDatabasePathSearch.setDisabled(True)
        self.lineSearchTerms.setDisabled(True)

        self.pushButtonDatabasePathSearch.setDisabled(True)
        self.searchPushButtonSearch.setDisabled(True)

        self.lineDatabasePathExport.setDisabled(True)
        self.lineFieldsExport.setDisabled(True)
        self.checkBoxAll.setDisabled(True)
        self.comboBoxSelectTable.setDisabled(True)
        self.comboBoxSelectFormat.setDisabled(True)

        self.dateTimeSince.setDisabled(True)
        self.dateTimeUntil.setDisabled(True)

        table = self.comboBoxSelectTable.currentText()
        file_format = self.comboBoxSelectFormat.currentText()
        print('Exporting table named: ' + table)
        columns = list(dict.fromkeys(
            ['created_at', 'user.screen_name', 'retweeted_status.user.screen_name', 'complete_text', 'lang'] + [
                _.strip() for _ in self.lineFieldsExport.text().split(',') if _ != '']))
        languages = 'all' if self.checkBoxAll.isChecked() else self.lineEditLanguages.text()
        conn = sqlite3.connect(self.lineDatabasePathExport.text())
        since = int(self.dateTimeSince.dateTime().toTime_t())
        until = (self.dateTimeUntil.dateTime().toTime_t())

        df = pd.DataFrame()
        i = 0

        while True:
            temp = pd.read_sql_query(
                'select response from ' + '`{}`'.format(table) + ' where timestamp >= {} and timestamp <= {}'.format(
                    since, until) + ' limit 10000' + ' offset ' + str(10000 * i), conn)
            if temp.empty or self.stop_exporting:
                break
            temp = json_normalize(temp.response.apply(json.loads))
            temp['complete_text'] = get_complete_text(temp)
            temp = temp[columns]
            df = pd.concat([df, temp], ignore_index=True)
            print(10000 * i)
            i += 1

        if not self.stop_exporting and not df.empty:
            if languages != 'all':
                df = df[df['lang'] in languages.split(',')]
                df = df.drop('lang', 1)

            if len(df) > 1048000:
                i = 0
                while True:
                    _ = df[1048000 * i: 1048000 * (i + 1)]
                    if _.empty:
                        break
                    else:
                        write_file(_, table, file_format, i + 1)
                        i += 1
            else:
                write_file(df, table, file_format)

            print('Done exporting ' + table)

        self.stop_exporting = False
        self.exporting = False
        self.exportPushButtonExport.setDisabled(False)
        self.cancelPushButtonExport.setDisabled(True)
        self.exportPushButtonExport.setText('Export')
        conn.close()

        self.lineAccessToken.setDisabled(False)
        self.lineAccessTokenSecret.setDisabled(False)
        self.lineConsumerKey.setDisabled(False)
        self.lineConsumerSecret.setDisabled(False)
        self.lineDatabasePathSearch.setDisabled(False)
        self.lineSearchTerms.setDisabled(False)

        self.pushButtonDatabasePathSearch.setDisabled(False)
        self.searchPushButtonSearch.setDisabled(False)
        self.dateTimeSince.setDisabled(False)
        self.dateTimeUntil.setDisabled(False)

    def select_file(self):
        self.lineDatabasePathSearch.setText(QFileDialog.getOpenFileName()[0])

    def select_file_export(self):
        self.lineDatabasePathExport.setText(QFileDialog.getOpenFileName()[0])

    def append_text(self, text):
        self.textEditOutput.textEditOutput.append(text)
        self.textEditOutput.textEditOutput.moveCursor(QtGui.QTextCursor.End)
        self.lineEditFound.setText(str(self.counter))

    def set_stop_searching(self):
        self.stop_searching = True

    def set_stop_exporting(self):
        self.stop_exporting = True

    def search(self):
        self.searchPushButtonSearch.setText('Searching...')
        self.searchPushButtonSearch.setDisabled(True)
        self.cancelPushButtonSearch.setDisabled(False)
        self.pushButtonDatabasePathSearch.setDisabled(True)

        self.lineAccessToken.setDisabled(True)
        self.lineAccessTokenSecret.setDisabled(True)
        self.lineConsumerKey.setDisabled(True)
        self.lineConsumerSecret.setDisabled(True)
        self.lineDatabasePathSearch.setDisabled(True)
        self.lineSearchTerms.setDisabled(True)

        self.lineDatabasePathExport.setDisabled(True)
        self.lineFieldsExport.setDisabled(True)
        self.checkBoxAll.setDisabled(True)
        self.comboBoxSelectTable.setDisabled(True)
        self.comboBoxSelectFormat.setDisabled(True)

        self.radioButtonSaveSingle.setDisabled(True)
        self.radioButtonSaveSeparatedly.setDisabled(True)
        self.radioButtonDontSave.setDisabled(True)

        self.dateTimeSince.setDisabled(True)
        self.dateTimeUntil.setDisabled(True)

        now = time()

        token = self.lineAccessToken.text()
        token_secret = self.lineAccessTokenSecret.text()
        consumer_key = self.lineConsumerKey.text()
        consumer_secret = self.lineConsumerSecret.text()
        terms = ','.join([_.strip() for _ in self.lineSearchTerms.text().split(',')])
        terms_list = terms.split(',')
        single_table_name = terms_list[0]
        single_table = self.radioButtonSaveSingle.isChecked()
        multiple_tables = self.radioButtonSaveSeparatedly.isChecked()
        dont_save = self.radioButtonDontSave.isChecked()
        conn = sqlite3.connect(self.lineDatabasePathSearch.text())

        cur = conn.cursor()

        for t in terms_list:
            cur.execute('CREATE TABLE IF NOT EXISTS ' + '`[{}]`'.format(
                t) + ' (\nid integer PRIMARY KEY,\ntimestamp INTEGER,\nresponse TEXT\n);')

        print('Initiating stream...')

        while self.searching:
            try:
                twitter_stream = TwitterStream(
                    auth=OAuth(token, token_secret, consumer_key, consumer_secret))

                iterator = twitter_stream.statuses.filter(track=terms, stall_warnings=True)

                print('Searching for {}'.format(terms_list))

                for tweet in iterator:
                    keys = tweet.keys()

                    if 'retweeted_status' in keys:
                        try:
                            text = tweet['retweeted_status']['extended_tweet']['full_text']
                        except KeyError:
                            text = tweet['retweeted_status']['text']
                    else:
                        try:
                            text = tweet['extended_tweet']['full_text']
                        except KeyError:
                            try:
                                text = tweet['text']
                            except KeyError:
                                continue

                    if single_table:
                        cur.execute('INSERT INTO ' + '`[{}]`'.format(
                            single_table_name) + '(timestamp,response)\nVALUES(?,?)',
                                    (int(time()), json.dumps(tweet)))
                        self.counter += 1

                    elif multiple_tables:
                        text_lower = text.lower()
                        for t in terms_list:
                            if t.lower() in text_lower:
                                cur.execute('INSERT INTO ' + '`[{}]`'.format(t) + '(timestamp,response)\nVALUES(?,?)',
                                            (int(time()), json.dumps(tweet)))
                                self.counter += 1
                                break

                    else:
                        self.counter += 1

                    if not (self.counter % 5000) and not dont_save:
                        conn.commit()
                        print('Committed at ' + str(int(time())))

                    if time() - now > 5:
                        self.textEditOutput.received_text.emit('@{}: {}'.format(tweet['user']['screen_name'], text))
                        now = time()

                    if self.stop_searching:
                        self.stop_searching = False
                        self.searching = False

                        self.lineAccessToken.setDisabled(False)
                        self.lineAccessTokenSecret.setDisabled(False)
                        self.lineConsumerKey.setDisabled(False)
                        self.lineConsumerSecret.setDisabled(False)
                        self.lineDatabasePathSearch.setDisabled(False)
                        self.lineSearchTerms.setDisabled(False)

                        self.pushButtonDatabasePathSearch.setDisabled(False)
                        self.searchPushButtonSearch.setDisabled(False)
                        self.searchPushButtonSearch.setText('Search')

                        self.lineDatabasePathExport.setDisabled(False)
                        self.lineFieldsExport.setDisabled(False)
                        self.checkBoxAll.setDisabled(False)
                        self.comboBoxSelectTable.setDisabled(False)
                        self.comboBoxSelectFormat.setDisabled(False)

                        self.radioButtonSaveSingle.setDisabled(False)
                        self.radioButtonSaveSeparatedly.setDisabled(False)
                        self.radioButtonDontSave.setDisabled(False)

                        self.dateTimeSince.setDisabled(False)
                        self.dateTimeUntil.setDisabled(False)

                        print('Stopped searching.')
                        break
            except Exception as e:
                traceback.print_exc()
                print(e)
                sleep(15)

    def start_searching(self):
        if not self.searching:
            print('Starting thread.')
            Thread(target=self.search, daemon=True).start()
            self.searching = True
            print('Returning from start_thread().')

    def start_exporting(self):
        if not self.exporting:
            print('Starting exporting thread.')
            Thread(target=self.export, daemon=True).start()
            self.exporting = True
            print('Returning from start_exporting_thread().')


def main():
    import sys

    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Backend()
    ui.setupUi(MainWindow)
    ui.init_stuff()
    MainWindow.show()
    sys.exit(app.exec_())


main()
