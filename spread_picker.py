#!/usr/bin/env python
# encoding: utf-8

# This is a script which pulls weekly picks for (currently) college football
# games from various sites. It will compare the spreads on each site and offer
# suggestions for picks based on a variety of criteria.

# Current supported sites (only for current weeks):
# [ ] collegefootballpoll.com (computer picks)
# [ ] oddsshark.com (computer and public picks)
# [ ] sportsline.com (public picks)

# Methodology (heuristics):
# - First, stick with the home team. More points, crowd advantage, better calls, etc.
# - Find spreads that are greater on alternate sites than officefootballpool
#   - When a computer has a much larger spread than the opening line OR when the
#       computer heavily favors the underdog, give an advantage to that team
# - Trust the computer picks more than the people. Finding these picks might
#       be good insight to find the 'value' pick.

# Key:
# ofp- Office Football Pool
# cfp- College Football Poll
# os- Odds Shark
# sl- Sports Line

# Code outline
#   - Start only with games available on officefootballpool
#   - Might have to do some normalization of names from different sites
#   - Each game will be a class.

import requests
from lxml import etree, html
from bs4 import BeautifulSoup
from urlparse import urlparse
import re

#ofp_url = 'http://www.officefootballpool.com/picks.cfm?p=1&sportid=5'
ofp_url = "http://www.officefootballpool.com/picks.cfm?sportid=5&p=1&thispoolid=117127"
cfp_url = "http://www.collegefootballpoll.com/weekly_picks.html"

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

        #self.ofp_home_line = ofp_home_line
        #self.ofp_away_line = ofp_away_line

    def add_cfp(self, cfp):
        """Add lines from cfp"""
        {'underdog': 'tulane', 'away': 'tulane', 'favorite': 'wake forest', 'computer': -15.26, 'home': 'wake forest', 'line': -17.0}
        if cfp['computer'] > 0:
            self.cfp_upset = True
        else:
            self.cfp_upset = False
        self.cfp_line = cfp['line']
        self.cfp_comp_line = cfp['computer']
        #print cfp


    #def __str__(self):
        #return '{0} @ {1}'.format(self.away, self.home) + '\n' + '{0} to {1}'.format(self.ofp_away_line, self.ofp_home_line)
        #return '{0} @ {1}'.format(self.away, self.home) + '\n' + '{0} to {1}'.format(self.ofp_away_line, self.ofp_home_line)

#class Ofp():
    #"""Office Football Pool page information"""

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
            "mich": "michigan"
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
    with open('./ofp.html') as ofp_htm:
        soup=BeautifulSoup(ofp_htm.read())
    #games = tree.xpath('//table[@title="std results"]/text()')
    table = soup.find("table", attrs={"class":"std results"})
    games_raw = [tr for tr in table.find_all("tr", attrs={"class":"college"})]
    for g in games_raw:
        teams = {}
        for ref in g.find_all("a"):
            if "title" in ref.attrs:
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
                home, away = parse_div(div.text)
                g = Game(home.lower(), away.lower(), teams[home]["team_spread"], teams[away]["team_spread"])
                games.append(g)
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
                computer = float(tds[3].text)
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


#GLOBAL
def is_same_team(v1, v2):
    if v1 == v2:
        return True
    elif v1 in v2:
        return True
    elif v2 in v1:
        return True


def eval_ofp_cfp(game):
    average_line = (game.line + game.cfp_line) / 2
    comp_diff = abs(average_line - game.cfp_comp_line)
    if comp_diff > 6:
        print vars(game)
        print average_line
        print comp_diff
        if game.cfp_comp_line < average_line:
            print 'Pick favorite:', game.favorite
        else:
            print 'Pick to cover:', game.underdog
        print '='*50



def main():
    games = parse_ofp()
    cfp_matchups = parse_cfp()

    for g in games:
        for cfp in cfp_matchups:
            if is_same_team(cfp["home"], g.home) and is_same_team(cfp["away"], g.away):
                g.add_cfp(cfp)
                eval_ofp_cfp(g)


if __name__ == "__main__":
    main()
