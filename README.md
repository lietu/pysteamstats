# PySteamStats

Statistics for Steam users.

PySteamStats connets to Steam HTTP APIs, fetches the list of owned games for a
Steam ID, then proceeds to ask Steam the pricing etc. information for the games.

After collecting the data it shows you a list of your games, the amount of hours
spent playing them, and the amount of money it cost in the specified region.

There are some issues with the Steam APIs I'm using, e.g. it doesn't return any
price for some games, I don't care that much, it's good enough for me. Feel free
to improve on this.

The APIs in use also provide a lot more information and it should be easy to
modify the tool to do something else.


## Compatibility

The code runs on Windows and *nix (tested on Linux), on both Python 2.7 and 3
(dunno, and don't care about older ones).


## Usage

Download pysteamstats.py or clone the repository. Then run one of the following:

```
python pysteamstats.py --help
python pysteamstats.py steam_id FI
python pysteamstats.py steam_id UK --mode write
python pysteamstats.py steam_id US --mode read
```

Replace US/UK/FI with whatever 2 character country code fits you best.

Write mode means that it writes the API responses to files unique by Steam ID
and country code.
Read mode means that it reads the API responses from those files.
These modes are probably only useful to developers that don't want to hit the
Steam APIs and wait for the responses all the time.


# Licensing

The code is released under new BSD and MIT licenses. Basically that means you can
do whatever you want with it, as long as you don't blame me if it breaks something.
However, it really shouldn't break anything.

More details in the LICENSE.md file.
