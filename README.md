# Tweet Watcher

A simple graphical user interface for searching and storing tweets in real time.

***
### Dependencies
* [Pandas](https://pypi.org/project/pandas/)
* [Openpyxl](https://pypi.org/project/openpyxl/)
* [PyQt5](https://pypi.org/project/PyQt5/)
* [Python Twitter Tools](https://github.com/sixohsix/twitter)
***
### Installation
```sh
$ python3 -m pip install git+git://github.com/sixohsix/twitter.git#twitter
$ python3 -m pip install tweetwatcher
```
Add to ```~/.local/bin``` to ```PATH``` if it isn't already.
***
### Usage
You will need a Twitter developer account to get the API tokens. You can create that [here](developer.twitter.com).
<br>Then just type tweetwatcher on your terminal emulator to open the app.
```sh
$ tweetwatcher
```
Once you open the app, you will need to fill the fields with the tokens and keys you got before searching for anything.
You can also create a ```credentials``` file at your user home (```~/``` or ```C:\Users\username```) like this:
```text
<access token>
<access token secret>
<consumer key>
<consumer key secret>
<path to database to store tweets>
```