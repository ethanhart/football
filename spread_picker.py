#!/usr/bin/env python
# encoding: utf-8

# This is a script which pulls weekly picks for (currently) college football
# games from various sites. It will compare the spreads on each site and offer
# suggestions for picks based on a variety of criteria.

# Current supported sites (only for current weeks):
# [x] collegefootballpoll.com (computer picks)
# [ ] oddsshark.com (computer and public picks)
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

        self.has_os = False
        #self.ofp_home_line = ofp_home_line
        #self.ofp_away_line = ofp_away_line

    def add_cfp(self, cfp):
        """Add lines from cfp"""

        if cfp['computer'] > 0:
            self.cfp_upset = True
        else:
            self.cfp_upset = False
        self.cfp_line = cfp['line']
        self.cfp_comp_line = cfp['computer']
        #print cfp

    def add_os(self, os):
        """Add lines from os"""

        if os['computer'] > 0:
            self.os_upset = True
        else:
            self.os_upset = False
        self.os_comp_line = os['computer']
        self.os_line = os['line']
        self.has_os = True
        #print cfp

    #def __str__(self):
        #return '{0} @ {1}'.format(self.away, self.home) + '\n' + '{0} to {1}'.format(self.ofp_away_line, self.ofp_home_line)
        #return '{0} @ {1}'.format(self.away, self.home) + '\n' + '{0} to {1}'.format(self.ofp_away_line, self.ofp_home_line)


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
            "ucf": "central florida",
            "no": "north",
            "usc": "southern california",
            "utep": "texas el paso"
            }

    if '#' in name:
        name = ' '.join(name.split()[1:])
    buff = []
    for s in name.split():
        if s in terms:
            buff.append(terms[s])
        else:
            buff.append(s)
    name = ' '.join(buff)
    return name


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
    #games = tree.xpath('//table[@title="std results"]/text()')
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
                #print urlparse('http://www.officefootballpool.com/' + ref.attrs["href"].replace('picks.cfm', ''))
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
                    #print div.text
                    #print "Likely OTB"
    return games


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
        if len(tds) == 6:
            if is_number(get_text(tds[2])) or get_text(tds[2]) == 'NL':
                favorite = get_text(tds[1])
                line = get_text(tds[2])
                if line != 'NL':
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
            else:
                pass
    return matchups


#GLOBAL
def parse_site(url):
    """Get the webpage, return the html tree"""
    page = requests.get(url)
    content =  page.content
    #tree = html.fromstring(page.content)
    #return tree

    soup = BeautifulSoup(content)
    return soup


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

            m = re.search('\((.*)\)', comp_ats.text)
            line = float(m.group(1))
            if line > 0:
                line = line * -1

            # Could potentially add some logic here to pick based on public
            # and computer ATS picks, but for now, just use the spread.

            matchup = {
                        "home": normalize_team(home),
                        "away": normalize_team(away),
                        "favorite": normalize_team(favorite),
                        "underdog": normalize_team(underdog),
                        "line": line,
                        "comp_line": comp_line
                      }

            matchups.append(matchup)

    return matchups


#GLOBAL
def is_same_team(v1, v2):
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


def print_game(game):
    average_line = (game.line + game.cfp_line) / 2
    comp_diff = abs(average_line - game.cfp_comp_line)
    #print vars(game)
    if game.home == game.favorite:
        home = game.home.upper()
        away = game.away
    else:
        away = game.away.upper()
        home = game.home
    print "Home: ", home
    print "Away: ", away
    print "Average line: ", average_line
    print "Computer line: ", game.cfp_comp_line
    print "Computer bonus: ", comp_diff
    if game.cfp_comp_line < average_line:
        print 'Pick favorite:', game.favorite
    else:
        print 'Pick to cover:', game.underdog
    print '='*50


#def eval_ofp_cfp(game):
def eval_game(game):
    # NEED TO AS OS LINE, WEIGHTS, ETC.
    lines = [game.line + game.cfp_line]
    comp_lines = [game.cfp_comp_line]
    if game.has_os:  # could add command line arg to enable/disable os
        lines.append(game.os_line)
        comp_lines.append(game.os_comp_line)
    average_line = sum(lines) / float(len(lines))
    average_comp_line = sum(comp_lines) / float(len(comp_lines))
    comp_diff = abs(average_line - average_comp_line)

    # CREATE WAGE SELECTION FUNCTION
    # TAKE MINIMUM FOR HALF WAGE, MULTIPLE BY 1.5 OR SOMETHING FOR FULL WAGE

    # Take the upset! But only for home teams
    if game.cfp_upset and game.underdog == game.home and comp_diff > 5:
        print "UPSET ALERT"
        if comp_diff > 8:
            print 'Wage Full'
        elif comp_diff > 5:
            print 'Wager Half'
        print_game(game)

    # Pick a favored home team where the model predicts a higher margin than the spread
    elif game.favorite == game.home and comp_diff > 3 and game.cfp_comp_line < average_line:
        print "Take the home team"
        if comp_diff > 6:
            print 'Wage Full'
        elif comp_diff > 3:
            print 'Wager Half'
        print_game(game)

    # Pick the home team to cover (not neccessarily an upset)
    elif game.underdog == game.home and comp_diff > 6 and game.cfp_comp_line > average_line:
        print "Take the home team to cover"
        if comp_diff > 8:
            print 'Wage Full'
        elif comp_diff > 6:
            print 'Wager Half'
        print_game(game)

    # Pick the away team
    elif game.favorite == game.away and comp_diff > 7  and game.cfp_comp_line < average_line:
        print "Take the away team"
        if comp_diff > 10:
            print 'Wage Full'
        elif comp_diff > 7:
            print 'Wager Half'
        print_game(game)

    # Pick a team who has a computer bonus of more than twelve points
    elif comp_diff > 12:
        print "Major line difference"
        print "Wage Full"
        print_game(game)

    #else:
        #print "Don't bet!"
        #print_game(game)

    #elif comp_diff > 0:
        #print "REST"
        #print_game(game)


def main():
    games = parse_ofp()
    cfp_matchups = parse_cfp()
    #os_matchups = parse_os(os_url)

    for g in games:
        for cfp in cfp_matchups:
            if is_same_team(cfp["home"], g.home) and is_same_team(cfp["away"], g.away):
                g.add_cfp(cfp)
                eval_game(g)

        #for os in os_matchups:
            #if is_same_team(os["home"], g.home) and is_same_team(os["away"], g.away):
                #g.add_os(os)
        #eval_game(g)


if __name__ == "__main__":
    main()
