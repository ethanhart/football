#!/usr/bin/env python
# encoding: utf-8

# This is a script which pulls weekly picks for (currently) college football
# games from various sites. It will compare the spreads on each site and offer
# suggestions for picks based on a variety of criteria.

# Current supported sites (only for current weeks):
# [x] collegefootballpoll.com (computer picks)
# [x] oddsshark.com (computer and public picks)
# [ ] sportsline.com (public picks)

# Methodology (heuristics):
# - First, stick with the home team. More points, crowd advantage, better calls, etc.
# - Find disparities in spreads compared to officefootballpool (find opportunities).
#   - When a computer has a much larger spread than the opening line OR when the
#       computer heavily favors the underdog, give an advantage to that team
# - Trust the computer picks more than the people. Finding these picks might
#       be good insight to find the 'value' pick.

# Key:
# ofp- Office Football Pool
# cfp- College Football Poll
# os- Odds Shark
# sl- Sports Line

import requests
from lxml import etree, html
from bs4 import BeautifulSoup
from urlparse import urlparse
import re

#ofp_url = 'http://www.officefootballpool.com/picks.cfm?p=1&sportid=5'
ofp_url = "http://www.officefootballpool.com/picks.cfm?sportid=5&p=1&thispoolid=117127"
cfp_url = "http://www.collegefootballpoll.com/weekly_picks.html"
os_url = "http://www.oddsshark.com/ncaaf/computer-picks"

class Game():
    def __init__(self, home, away, ofp_home_line, ofp_away_line):
        """Start with what we know: home, away, and
        the spread from officefootballpool. This spread
        will be the starting point for any pick"""

        self.home = home
        self.away = away
        if ofp_home_line < ofp_away_line:
            self.favorite = home
            self.underdog = away
            self.line = ofp_home_line
        else:
            self.favorite = away
            self.underdog = home
            self.line = ofp_away_line

        self.lines = [self.line]
        self.comp_lines = []
        self.has_os = False

    def avg_comp_line(self):
        return round(sum(self.comp_lines)/float(len(self.comp_lines)))

    def avg_line(self):
        return round(sum(self.lines)/float(len(self.lines)))

    def add_cfp(self, cfp):
        """Add lines from cfp"""

        if cfp['computer'] > 0:
            self.cfp_upset = True
        else:
            self.cfp_upset = False
        if is_number(cfp['line']):
            self.lines.append(cfp['line'])
        self.comp_lines.append(cfp['computer'])

    def add_os(self, os):
        """Add lines from os"""

        if os['computer'] > 0:
            self.os_upset = True
        else:
            self.os_upset = False
        self.lines.append(os['line'])
        self.comp_lines.append(os['computer'])
        self.has_os = True

    def print_game(self):
        avg_line = self.avg_line()
        avg_comp_line = self.avg_comp_line()
        comp_diff = abs(avg_line - avg_comp_line)
        if self.home == self.favorite:
            home = self.home.upper()
            away = self.away
        else:
            away = self.away.upper()
            home = self.home

        print "Home: ", home
        print "Away: ", away
        print "Average line: ", avg_line
        print "Computer line: ", avg_comp_line
        print "Computer bonus: ", comp_diff
        if avg_comp_line < avg_line:
            print 'Pick favorite:', self.favorite
        else:
            print 'Pick to cover:', self.underdog
        print '='*50


#GLOBAL
def parse_site(url):
    """Get the webpage, return the html tree"""

    page = requests.get(url)
    content =  page.content
    soup = BeautifulSoup(content)
    return soup


#GLOBAL
def normalize_team(name):
    """Normalize team names"""

    name = name.lower()
    name = re.sub('\(.*\)', '', name)
    name = name.strip()
    terms = {
            "st.": "state",
            "ill": "illinois",
            "mich": "michigan",
            "fiu": "florida international",
            "fau": "florida atlantic",
            "atl.": "atlantic",
            "ucf": "central florida",
            "no": "north",
            "usc": "southern california",
            "utep": "texas el paso",
            "louisiana-monroe": "ul monroe",
            "louisiana-lafayette": "ul lafayette",
            "n.c.": "north carolina",
            "smu": "southern methodist"
            }

    if '#' in name:  # remove ranking info
        name = ' '.join(name.split()[1:])
    buff = []
    for s in name.split():
        if s in terms:
            buff.append(terms[s])
        else:
            buff.append(s)
    name = ' '.join(buff)
    return name


#GLOBAL
def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        pass

    try:
        import unicodedata
        unicodedata.numeric(s)
        return True
    except (TypeError, ValueError):
        pass

    return False


#GLOBAL
def get_text(s):
    return s.text.encode('utf-8')


#GLOBAL
def is_same_team(v1, v2):
    """A overly verbose way to check if names
    are referring to the same team"""

    if v1 == v2:
        return True
    elif v1 in v2 and "state" not in v1 and "state" not in v2:
        return True
    elif v1 in v2 and "state" in v1 and "state" in v2:
        return True
    elif v2 in v1 and "state" not in v1 and "state" not in v2:
        return True
    elif v2 in v1 and "state" in v1 and "state" in v2:
        return True


#OFP
def parse_href(href):
    """Get parameters of href for ofp"""

    params = {}
    for i in href.split('&'):
        split = i.split('=')
        key = split[0]
        value = split[1]
        params[key] = value
    return params


#OFP
def parse_div(div_text):
    """Get home and away teams for ofp"""

    split = div_text.split('@')
    away = normalize_team(' '.join(split[0].split()[:-1]))
    home = normalize_team(' '.join(split[-1].split()[:-1]))
    return home, away


#OFP
def parse_ofp():
    """Read in the weeks games, return a 'game' object for each game.
    Currently requires manual sign in and saving html to ofp.html"""

    games = []
    with open('./ofp2.html') as ofp_htm:
        soup=BeautifulSoup(ofp_htm.read())
    table = soup.find("table", attrs={"class":"std results"})
    games_raw = [tr for tr in table.find_all("tr", attrs={"class":"college"})]
    for g in games_raw:
        teams = {}
        for ref in g.find_all("a"):
            if "onclick" in ref.attrs:
                if "You have already risked the maximum amount of shares on" in ref.attrs["onclick"]:
                    params = {}
                    m = re.search('maximum amount of shares on (.*)\.', ref.attrs["onclick"])
                    team_name = normalize_team(m.group(1))
                    team_abbrv = ref.text.split()[0]
                    team_spread = ref.text.split()[-1]
                    params["team_name"] = team_name
                    params["team_abbrv"] = team_abbrv.lower()
                    params["team_spread"] = float(team_spread)
                    params["line"] = float(team_spread)
                    teams[team_name] = params
            elif "title" in ref.attrs:
                params = parse_href(re.sub('.*\?', '', ref.attrs["href"]))
                m = re.search('Pick (.*) to cover the spread', ref.attrs["title"])
                team_name = normalize_team(m.group(1))
                team_abbrv = ref.text.split()[0]
                team_spread = ref.text.split()[-1]
                params["team_name"] = team_name
                params["team_abbrv"] = team_abbrv.lower()
                params["team_spread"] = float(team_spread)
                teams[team_name] = params
        for div in g.find_all("div"):
            if '@' in div.text:
                try:
                    home, away = parse_div(div.text)
                    g = Game(home.lower(), away.lower(), teams[home]["team_spread"], teams[away]["team_spread"])
                    games.append(g)
                except KeyError:
                    pass
    return games


#CFP
def is_cfp_header(tds):
    tds_text = ' '.join([x.text.strip() for x in tds])
    if tds_text == 'Score Favorite Line (Open) Computer Underdog Score':
        return True
    else:
        return False


#CFP
def parse_cfp():
    """Parse College Football Poll"""

    matchups = []
    soup = parse_site(cfp_url)
    tables = soup.find("table", attrs={"class":"contentTable"})
    div = tables.find("div", attrs={"id":"IntelliTXT"})
    trs = div.find_all("tr")
    for tr in trs:
        tds = tr.find_all("td")
        if len(tds) == 6 and not is_cfp_header(tds):
            favorite = get_text(tds[1])
            line = get_text(tds[2])
            if is_number(line):  # != 'NL' or sometimes empty
                line = float(line)
            computer = float(tds[3].text.replace('*', ''))
            underdog = get_text(tds[4])
            if favorite.isupper():
                home = favorite
                away = underdog
            else:
                home = underdog
                away = favorite
            matchup = {
                        "home": normalize_team(home),
                        "away": normalize_team(away),
                        "favorite": normalize_team(favorite),
                        "underdog": normalize_team(underdog),
                        "line": line,
                        "computer": computer
                        }
            matchups.append(matchup)

    return matchups


#OS
def parse_os(url):
    """Parse the Odds Shark webpage"""

    soup = parse_site(url)
    tables = soup.find_all("table", attrs={"class":"base-table"})
    matchups = []
    for i in tables:
        tds = i.find_all("td")
        if len(tds) == 12:
            teams = i.find("caption").text.split("Matchup")
            home = teams[1].strip().lower()
            away = teams[0].strip().lower()
            scores = tds[1].text.split(' - ')
            home_score = float(scores[1])
            away_score = float(scores[0])
            comp_line = abs(home_score - away_score) * -1
            if home_score > away_score:
                favorite = home
                underdog = away
            else:
                favorite = away
                underdog = home
            total = tds[2]
            comp_ats = tds[4]
            comp_total = tds[5]
            public_ats = tds[7]
            public_total = tds[8]
            consensus_ats = tds[10]
            consensus_total = tds[11]

            if comp_ats.text.strip() == 'Push' and public_ats.text.strip() != 'Push':
                m = re.search('\((.*)\)', public_ats.text)
                line = float(m.group(1))
            else:
                m = re.search('\((.*)\)', comp_ats.text)
                line = float(m.group(1))
            if line > 0:
                line = line * -1

            matchup = {
                        "home": normalize_team(home),
                        "away": normalize_team(away),
                        "favorite": normalize_team(favorite),
                        "underdog": normalize_team(underdog),
                        "line": line,
                        "computer": round(comp_line, 2)
                      }

            matchups.append(matchup)

    return matchups


class Wager():
    def __init__(self, comp_diff, max_bet):
        self.comp_diff = comp_diff
        self.max_bet = max_bet

    def get_bet(self, *brakes):
        """Determine how much to bet based on
        specified differences in lines"""

        bet = 0
        for e,b in enumerate(brakes):
            numerator = e + 1
            scale =  numerator/float(len(brakes))
            if self.comp_diff > b:
                bet = scale * self.max_bet
        print 'Wager: ', bet


def eval_game(game, max_bet):
    avg_line = game.avg_line()
    avg_comp_line = game.avg_comp_line()
    comp_diff = abs(avg_line - avg_comp_line)
    wager = Wager(comp_diff, max_bet)

    # Take the upset! But only for home teams
    if game.cfp_upset and game.underdog == game.home and comp_diff > 5:
        print "UPSET ALERT"
        wager.get_bet(5, 8)
        game.print_game()
        #print_game(game)

    # Pick a favored home team where the model predicts a higher margin than the spread
    elif game.favorite == game.home and comp_diff > 3 and avg_comp_line < avg_line:
        print "Take the home team"
        wager.get_bet(3, 6)
        game.print_game()

    # Pick the home team to cover (not neccessarily an upset)
    elif game.underdog == game.home and comp_diff > 6 and avg_comp_line > avg_line:
        print "Take the home team to cover"
        wager.get_bet(6, 8)
        game.print_game()

    # Pick the away team
    elif game.favorite == game.away and comp_diff > 7 and avg_comp_line < avg_line:
        print "Take the away team"
        wager.get_bet(7, 10)
        game.print_game()

    # Pick a team who has a computer bonus of more than twelve points
    elif comp_diff > 12:
        print "Major line difference"
        print "Wager: ", max_bet
        game.print_game()


def main():
    games = parse_ofp()
    cfp_matchups = parse_cfp()
    os_matchups = parse_os(os_url)
    max_bet = 315
    include_os = True

    for g in games:
        if include_os:
            for os in os_matchups:
                if is_same_team(os["home"], g.home) and is_same_team(os["away"], g.away):
                    g.add_os(os)
        for cfp in cfp_matchups:
            if is_same_team(cfp["home"], g.home) and is_same_team(cfp["away"], g.away):
                g.add_cfp(cfp)
                eval_game(g, max_bet)


if __name__ == "__main__":
    main()
