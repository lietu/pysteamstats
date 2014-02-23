#!/usr/bin/env bash

from decimal import Decimal, getcontext
import argparse
import json
import logging
import time
import xml.etree.ElementTree as ET


try:
    # Python 2
    from urllib2 import urlopen
except ImportError:
    # Python 3
    from urllib.request import urlopen


def _get_log():
    """Set up logging with some decent output format"""

    formatter = logging.Formatter('%(asctime)s [%(levelname)8s] %(message)s')

    logger = logging.getLogger('PySteamStats')
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler('pysteamstats.log')
    ch = logging.StreamHandler()

    fh.setLevel(logging.DEBUG)
    ch.setLevel(logging.DEBUG)

    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger

log = _get_log()


class PySteamStats(object):
    """Get Steam game statistics for a user's account"""

    userUrl = "http://steamcommunity.com/id/{steam_id}/games?tab=all&xml=1"
    appUrl = "http://store.steampowered.com/api/appdetails/" \
        "?appids={appIDs}&cc={country}&l=english&v=1"

    def run(self):
        """Get the games data for the user"""

        options = self._parse_args()
        games = self._get_games(options.steam_id, options.mode)

        log.info("Found {} games for user {}".format(
            len(games), options.steam_id
        ))

        self._get_app_data(
            games, options.steam_id, options.country, options.mode
        )

        total_price = sum([game["value"] for game in games])

        currency = "???"
        errors = 0
        for game in games:
            if game["currency"] != "???":
                currency = game["currency"]
            else:
                errors += 1

        log.info("Total value for games: {:.2f} {}".format(
            total_price, currency
        ))
        log.info("Errors with {} games.".format(errors))

        print("")
        print(" ----- Your Steam games list is below ----- ")
        print("")
        for game in sorted(games, key=lambda g: g["name"]):
            self._print_game(game)

    def _parse_args(self):
        """Parse arguments into options"""

        parser = argparse.ArgumentParser(
            description="Get the games list for a Steam account"
        )

        parser.add_argument(
            "steam_id", help="Steam username or account ID"
        )

        parser.add_argument(
            "country", help="2 character country code, e.g. \"FI\". Will fetch"
            " game data for that country from Steam API."
        )

        parser.add_argument(
            "--mode", required=False, choices=['read', 'write', 'normal'],
            help="Running mode, read, write or normal. Write mode writes "
            "Steam API responses to files, read mode reads those files instead"
            " of making HTTP requests"
        )
        parser.set_defaults(mode="normal")

        options = parser.parse_args()
        options.country = options.country.upper()

        return options

    def _get_games(self, steam_id, mode):
        """Get the games list for this user"""

        root = self._get_game_xml(steam_id, mode)
        games = self._extract_games(root)
        return games

    def _get_app_data(self, games, steam_id, country, mode):
        """Collect the application data off the Steam API for the games"""

        groups = self._get_groups(games)
        log.debug("Loading application datas in {} groups".format(len(groups)))

        for index, group in enumerate(groups):
            if index > 0 and mode != "read":
                # Try not to be an ass and make too many requests too fast
                time.sleep(1)

            appIDs = [game["appID"] for game in group]
            fname = "apps_{}_{}_{}.json".format(steam_id, country, index)

            if mode == "read":
                log.info("Reading from {}".format(fname))
                with open(fname, 'r') as f:
                    content = f.read()
            else:
                url = self.appUrl.format(
                    appIDs=",".join(appIDs),
                    country=country
                )
                log.debug("Requesting {}".format(url))

                f = urlopen(url)
                content = f.read().decode('utf8')

            if mode == "write":
                log.info("Writing to {}".format(fname))
                with open(fname, 'w') as f:
                    f.write(content)

            data = json.loads(content)

            for game in group:
                gamedata = data[game["appID"]]
                if (not "data" in gamedata or
                        not "price_overview" in gamedata["data"]):

                    log.error("Error with game {}, id {} in group {}".format(
                        game["name"], game["appID"], index
                    ))
                    continue

                price_data = data[game["appID"]]["data"]["price_overview"]
                price = price_data["final"]

                game["currency"] = price_data["currency"]
                game["value"] = Decimal("{}.{}".format(
                    int(price / 100),
                    price % 100
                ))

                try:
                    log.debug("{} seems to cost {} {} atm".format(
                        game["name"], game["value"], game["currency"]
                    ))
                except UnicodeEncodeError:
                    log.debug("{} seems to cost {} {} atm".format(
                        game["name"].encode("utf-8"),
                        game["value"],
                        game["currency"]
                    ))

    def _get_groups(self, games, group_size=10):
        """Generate groups of the given games suitable for API calls"""

        groups = []

        group = []
        for game in games:
            group.append(game)
            if len(group) >= group_size:
                groups.append(group)
                group = []

        if len(group) > 0:
            groups.append(group)

        return groups

    def _get_game_xml(self, steam_id, mode):
        """Get the XML list of games"""

        fname = "games_{}.xml".format(steam_id)

        if mode == "read":
            log.info("Reading from {}".format(fname))
            with open(fname, 'rb') as f:
                content = f.read()
        else:
            url = self.userUrl.format(steam_id=steam_id)
            log.debug("Requesting {}".format(url))

            f = urlopen(url)
            content = f.read()

        if mode == "write":
            log.info("Writing to {}".format(fname))
            with open(fname, 'wb') as f:
                f.write(content)

        try:
            root = ET.fromstring(content)
        except UnicodeEncodeError:
            root = ET.fromstring(content.encode('utf-8'))

        return root

    def _extract_games(self, root):
        """Extract the names of the games from the XML tree"""

        games = []
        for game_elem in root.iter("game"):
            game = {
                "value": Decimal("0.00"),
                "currency": "???",
                "hoursOnRecord": 0
            }

            for key in ["appID", "name", "hoursOnRecord"]:
                for elem in game_elem.iter(key):
                    game[key] = elem.text

            games.append(game)

        return games

    def _print_game(self, game):
        """Print out a game in the list"""

        hours = game["hoursOnRecord"]
        value = game["value"]
        currency = game["currency"]

        def _print(name):
            print("{} ({} hrs / {} {})".format(
                name, hours, value, currency
            ))

        try:
            _print(game["name"])
        except UnicodeEncodeError:
            # Some games have odd characters in them that cause errors
            _print(game["name"].encode('ascii', 'replace').decode())


if __name__ == "__main__":
    # Set decimal precision
    getcontext().prec = 2

    pss = PySteamStats()
    pss.run()
