# coding: utf-8
"""
Take input from Bob's site and render it in Bootstrap so the site is actually legible on a mobile device.

TODO: add search that autcompletes based on trip report title (or more ambitiously, the peak names in the TR). In
    the autocomplete list, show the TR name and date in yyyy/mm/dd format. Could also statically generate front page
    10 minutes after every hour and serve that, while still dynamically rendering the individual TRs.
TODO: Add previously climbed
TODO: Add title photo
"""
import requests
import re
from flask import Flask, render_template, redirect
from flask_bootstrap import Bootstrap
from bs4 import BeautifulSoup, NavigableString, Tag

app = Flask(__name__)
bootstrap = Bootstrap(app)

# The two settings
bob_index = 'https://www.snwburd.com/bob/'
report_prefix = 'https://www.snwburd.com/bob/trip_reports/'


# Functions
def get_soup(url: str) -> object:
    """
    Parse url and return a BeautifulSoup4 object.
    """
    result = requests.get(url)
    soup = BeautifulSoup(result.text, 'lxml')
    return soup


def get_headers(soup: object) -> dict:
    """
    Put all of the relevant page content but for the trip report titles/urls in a dictionary and return it.
    """
    title = soup.title.text
    title_text = soup.td.text
    title_text = title_text.strip('\n')  # .text returns a string with newline characters.
    last_update = soup.i
    disclaimer = soup.nobr.find_next('p').find_next('p').text
    disclaimer = disclaimer.strip('\n')
    challenge_year = soup.find_all(href=re.compile('challenge/'))[1].get('href').lstrip(
        'challenge/')  # Get Challenge year

    headers = {'title': title, 'title_text': title_text, 'last_update': last_update, 'disclaimer': disclaimer,
               'challenge_year': challenge_year}
    # Return the dictionary for use with the Jinja2 template.
    return headers


def get_trip_reports(soup: object) -> list:
    """
    Iterate through each year's trip reports and return a list. NOTE: a 'year' here is really just a collection of
    trip reports. So '2018 Sierra Peaks' and '2018 Other Peaks' are both unique 'years' here. I should have probably
    thought more about what to call them.
    """
    yearly_reports = soup.find_all('font')  # By a quirk of luck, <font> is only used in the yearly trip report headers.
    # Iterate through the list of yearly reports.
    reports = []  # Create a single list to hold all reports to pass to Jinja2.

    for index, report_set in enumerate(yearly_reports):
        table = report_set.find_parent('table').find_all('tr')  # The parent table every set's report links in <td>
        # Go through each year's table and add each individual report to that year's list.
        reports_for_year = []
        for index, trip in enumerate(table):
            tr_info = {}  # Make a dictionary for each TR entry within the year.
            if index > 0:  # > 0 always catches actual trip reports; 0 is the section title/year.
                tr_info['date'] = trip.td.text
                tr_info['name'] = trip.td.find_next().a.text
                url = trip.td.find_next().a.get('href')
                tr_info['url'] = url.split('/')[-1]  # Returns 'report.html' only.
                # Just as the next <td> has an anchor tag, if there's a new TR, it will *also* have an img tag.
                new = trip.td.find_next().img  # Returns False if no match.
                if new:
                    tr_info['new'] = True
                reports_for_year.append(tr_info)  # Add this trip's data to the list for this 'year'.
            elif index == 0:
                reports_for_year.append(trip.text)  # The year is always at index[0]
        reports.append(reports_for_year)
    return reports


def get_report(soup: object) -> dict:
    """
    Get a single trip report and put the relevant items into dictionaries and lists as necessary for display in
    a Jinja2 template.
    """
    result = {}

    def url_rewrite(url: str, prefix: str) -> str:
        """
        Take a URL and a prefix (photo, person, peak, map) and return the a rewritten URL linking to Bob's site.
        """
        prefixes = {
            'photo': 'https://www.snwburd.com/bob/trip_photos/',
            'person': 'https://www.snwburd.com/bob/people/',
            'peak': 'https://www.snwburd.com/dayhikes/peak/',
            'map': 'https://www.snwburd.com/bob/maps/',
            'profile': 'https://www.snwburd.com/bob/maps/',
            'gpx': 'https://www.snwburd.com/bob/trip_maps/',
        }
        if prefix in ['photo', 'peak']:  # The last two segments are specific to the particular URL.
            url_double_tail = url.split('/')[-2:]
            url_double_tail = url_double_tail[0] + '/' + url_double_tail[1]
            result = prefixes[prefix] + url_double_tail
        # elif prefix == 'person' or prefix == 'map':  # Only the last segment is particular to the URL.
        elif prefix in ['person', 'map', 'profile', 'gpx']:  # Only the last segment is particular to the URL.
            url_tail = url.split('/')[-1]
            result = prefixes[prefix] + url_tail
        else:
            result = 'Something went wrong'

        return result

    def get_participants(soup: object) -> list:
        """
        Parse the soup and return a list of dictionaries of the format:
        {'name': 'Person Name', 'url': 'https://www.snwburd.com/bob/people/Person_Name.html'}
        """
        result = soup.find_all(href=re.compile('/bob/people'))

        names = []  # put the name and corresponding url in a dictionary and add the dictionary to the list.
        for name in result:
            d = {'name': name.text, 'url': url_rewrite(name.get('href'), 'person')}  # rewrite URL here.
            names.append(d)

        return names

    def get_peaks(soup: object) -> list:
        """
        Parse the soup and return a list of dictionaries of the format:
        {'name': 'Peak Name', 'url': 'https://www.snwburd.com/dayhikes/peak/<peak_id>/<peak_name>'}
        """
        result = soup.find_all(href=re.compile('/dayhikes/peak'))

        peaks = []
        for peak in result:
            d = {'name': peak.text.lstrip(' '), 'url': url_rewrite(peak.get('href'), 'peak')}
            peaks.append(d)

        return peaks

    def get_gpxes(soup: object) -> list:
        """
        Parse the soup and return a list of dictionaries of the format:
        {'name': 'x', 'url': 'https://www.snwburd.com/bob/trip_maps/<trip_name>.gpx'}
        """
        result = soup.find_all(href=re.compile('/trip_maps/'))

        gpxes = []
        for gpx in result:
            d = {'name': gpx.text, 'url': url_rewrite(gpx.get('href'), 'gpx')}
            gpxes.append(d)

        return gpxes

    def get_maps(soup: object) -> list:
        """
        Parse the soup and return a list of dictionaries of the format:
        maps: {'name': 'x', 'url': 'https://www.snwburd.com/bob/maps/<map>.html'}
        """
        result = soup.find_all(href=re.compile('/maps/'))

        maps = []
        for map_drawing in result:
            if 'profile' not in map_drawing.get('href'):  # Filter out profile links, as they're (nearly) identical.
                d = {'name': map_drawing.text, 'url': url_rewrite(map_drawing.get('href'), 'map')}
                maps.append(d)

        return maps

    def get_profiles(soup: object) -> list:
        """
        Parse the soup and return a list of dictionaries of the format:
        https://www.snwburd.com/bob/maps/peak_4,020ft_n06_1_1.html
        """
        result = soup.find_all(href=re.compile('/maps/'))

        profiles = []
        for profile in result:
            if 'profile' in profile.get('href'):  # Filter out map links, as they're (nearly) identical.
                d = {'name': profile.text, 'url': url_rewrite(profile.get('href'), 'profile')}
                profiles.append(d)

        return profiles

    def get_tr_body(soup: object) -> str:
        """
        Parse the soup to return the trip report body text. After trying a lot of parsing tricks with BeautifulSoup,
        I realized I could just convert all of the soup to a string, use the .replace() string method to replace
        the code that was creating the scrollbar. Though this created a lot of newlines ('\n'), they were easily
        stripped.

        This made the resulting HTML one giant block, so it's run through BS again to prettify for anyone who cares
        to view the source.
        """
        soup = soup.find(id='scrollbox')
        soup = str(soup)  # Cast as string to .replace() scrollbar code. Note: this creates many newlines.
        soup = soup.replace(' style="height:auto;overflow-y:scroll"', '').replace('\n', '')  # Remove newlines.
        soup = BeautifulSoup(soup, 'lxml')  # Make it HTML again so it can be prettified for source viewing.
        soup = soup.prettify()
        return soup

    def get_date(soup: object) -> str:
        """
        Parse the soup and return the date. Not sure it makes sense to have this function...
        """
        if soup.b:
            result = soup.b.text
        else:
            result = None

        return result

    def get_comments(soup: object) -> iter:  # Actually a generator, but whatever.
        """
        Parse the soup and return the comments as a generator.

        This involves iterating through the .next_elements that follow the trip report, stopping when the first <span>
        tag is found. Because people's names get printed twice by default, 'continue' past NavigableStrings with
        <b> Tags immediately preceding them, as that Navigable string will be a commenter's name, just as the <b> tag
        will be.
        """
        start = soup.find(id='scrollbox')  # Start at the text of the trip report
        start = start.next_sibling  # Move to the next_sibling (i.e. the end of the report).
        for i, v in enumerate(start.next_elements):
            if isinstance(v, NavigableString) and isinstance(v.previous, Tag):
                if v.previous.name == 'b':
                    continue  # Filter out the duplicate name that follows the name in the bold tag.
            yield v  # Yield only once we've filtered lines out.
            if isinstance(v, Tag):
                if v.name == 'span':
                    break  # <span> marks the end of the comments section.

    def get_last_updated(soup: object) -> list:
        """
        Parse the soup and return a few things, including the last updated time, as a list of dictionaries:
        - Last updated time; and
        - Contact info
        """
        result = {}

        soup = soup.find(href=re.compile('/bob/index.html'))
        result['last_updated'] = soup.find_next('i')  # Matches last updated.
        result['contact'] = soup.find_next('i').find_next('i')  # Matches contact info.

        return result

    # Call the functions above to compile the master dictionary for passing to the Jinja2 template.
    result['participants'] = get_participants(soup)  # Add the list of name-dictionaries.
    result['peaks'] = get_peaks(soup)  # Add the list of name-dictionaries.
    result['gpxes'] = get_gpxes(soup)  # ""
    result['maps'] = get_maps(soup)
    result['profiles'] = get_profiles(soup)
    result['body'] = get_tr_body(soup)
    result['date'] = get_date(soup)
    result['comments'] = get_comments(soup)  # Note: returns a generator
    result['last_updated'] = get_last_updated(soup).get('last_updated').text
    result['contact'] = get_last_updated(soup).get('contact').text

    # Add in the rest of the data
    result['photos'] = photos = url_rewrite(soup.find_all(href=re.compile('/trip_photos/'))[1].get('href'), 'photo')

    return result

# A small bit of Flask
@app.route('/')
def index():
    """
    Get the index of Bob's site and render with Bootstrap for display on mobile.
    """
    soup = get_soup(bob_index)  # Make the soup.
    if "403 Forbidden" in soup.title:
        return "It looks as if the script can't connect to snwburd.com. That's not good."
    headers = get_headers(soup)  # Get a dictionary of the 'headers' content.
    reports = get_trip_reports(soup)  # Get a list of the trip report content.
    return render_template('index.html', title='MobileBurd', headers=headers, reports=reports)


@app.route('/report/<report_url>')
def report(report_url):
    """
    Create a trip report from the URL supplied by the link from the index page
    """
    soup = get_soup('https://www.snwburd.com/bob/trip_reports/' + report_url)
    if "403 Forbidden" in soup.title:
        return "It looks as if the script can't connect to snwburd.com. That's not good."
    result = get_report(soup)
    return render_template('trip_report.html', title='MobileBurd', report=result)


@app.route('/trip_photos/<path:page>')
def trip_photos(page):
    """
    Redirect all 'trip_photos' URLs to Bob's site so I don't have to seek out and rewrite the URLs within the body of
    each trip report.
    """
    prefix = 'https://www.snwburd.com/bob/trip_photos'
    return redirect(f'{prefix}/{page}')

