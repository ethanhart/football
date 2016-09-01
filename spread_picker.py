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

class Game():
    def __init__(self, home, away, ofp_home_line, ofp_away_line):
        """Start with what we know: home, away, and
        the spread from officefootballpool. This spread
        will be the starting point for any pick"""
        self.home = home
        self.away = away
        self.ofp_home_line = ofp_home_line
        self.ofp_away_line = ofp_away_line

    def __str__(self):
        return '{0} @ {1}'.format(self.away, self.home) + '\n' + '{0} to {1}'.format(self.ofp_away_line, self.ofp_home_line)


def parse_site(url):
    """Get the webpage, return the html tree"""
    page = requests.get(url)
    content =  page.content
    #tree = html.fromstring(page.content)
    #return tree

    soup = BeautifulSoup(content)
    return soup


##### OFP ##############

def parse_href(href):
    """Get parameters of href"""
    params = {}
    for i in href.split('&'):
        split = i.split('=')
        key = split[0]
        value = split[1]
        params[key] = value
    return params


def parse_div(div_text):
    """Get home and away teams"""

    split = div_text.split('@')
    away = ' '.join(split[0].split()[:-1])
    home = ' '.join(split[-1].split()[:-1])
    return home, away

def parse_ofp():
    """Read in the weeks games, return a 'game' object for each game.

    Currently requires manual sign in and saving html to ofp.html"""
    with open('./ofp.html') as ofp_htm:
        soup=BeautifulSoup(ofp_htm.read())
    #print soup
    #soup = parse_site(ofp_url)
    #print soup
    #games = tree.xpath('//table[@title="std results"]/text()')
    table = soup.find("table", attrs={"class":"std results"})
    #print table
    games_raw = [tr for tr in table.find_all("tr", attrs={"class":"college"})]
    for g in games_raw:
        #print [tag.attrMap['href'] for tag in g.find_all('a', {'href': True})]
        teams = {}
        for ref in g.find_all("a"):
            if "title" in ref.attrs:
                params = parse_href(re.sub('.*\?', '', ref.attrs["href"]))
                #print urlparse('http://www.officefootballpool.com/' + ref.attrs["href"].replace('picks.cfm', ''))
                m = re.search('Pick (.*) to cover the spread', ref.attrs["title"])
                team_name = m.group(1)
                team_abbrv = ref.text.split()[0]
                team_spread = ref.text.split()[-1]
                params["team_name"] = team_name
                params["team_abbrv"] = team_abbrv
                params["team_spread"] = team_spread
                teams[team_name] = params
        for div in g.find_all("div"):
            if '@' in div.text:
                home, away = parse_div(div.text)
                g = Game(home, away, teams[home]["team_spread"], teams[away]["team_spread"])
                print g
                #if home in teams:
                    #teams[home]["loc"] = "home"
                #if away in teams:
                    #teams[away]["loc"] = "away"

def main():
    parse_ofp()


if __name__ == "__main__":
    main()
