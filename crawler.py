import wikipedia as wiki
import pandas as pd
import json
import re
from datetime import date, datetime, timedelta
from unidecode import unidecode
from bs4 import BeautifulSoup
from pprint import pprint


global link_search_results      # probs a useless variable already?
FILENAME = 'results'    # str(datetime.now()).replace(':','.')[5:16]
now = str(datetime.now())
userinput = ''
search_query, search_results, new_finds, write_to_file = [],[],[],[]
df_rels = pd.DataFrame()

def main():
    """
    Searches for relationships between Wikipedia pages based on user query.
    Saves output to text and json files. Info is saved for future searches. 
    """
    user_input_search()
    with open('results/search_archive.json', 'r') as f:
        global archive
        try:
            archive = json.loads(json.load(f))
        except json.decoder.JSONDecodeError:
            print('No content in search archive.')
            archive = []
            pass

        [search_in_wiki(entry) for entry in search_query]
        print('Data collection completed.') 

    [write_to_file.append({
            'id':page['title'],
            'content':find_relationship(page, search_results)
        }) for page in search_results]
    write_to_files()


def user_input_search():
    """Accepts search input from user."""
    print('Input all the pages you want to search. Type "search" when done.')
    while True:
        userinput = input()
        if userinput.upper()=='SEARCH':
            if len(search_query) < 2:
                print('ERR: Please enter at least 2 pages to search.')
            else:
                break
        elif userinput.lower() in [i.lower() for i in search_query]:
            print('ERR: You have already entered that value. Please input another.')
        elif not userinput:
            print('ERR: Please input a value.')
        else:
            search_query.append(*userinput.split('\n'))    

def search_in_wiki(entry):     #search_results may be unnecessary
    """
    Searches Wikipedia and search_archive.json (if applicable) based on user query.
    Appends results to search_query array. New queries are added to the new_finds array,
    later to be added to search_archive.json.
    """
    try:
        for saved_entry in archive:
            if entry.lower() in saved_entry['title'].lower():
                print(entry + ' found in saved file.')
                search_results.append(saved_entry)
                return
    except: pass

    try:
        for session_entry in search_results:
            if entry.lower() in session_entry['title'].lower():
                print(entry + ' exists in current session.')
                return
    except: pass

    print('Collecting data for {}...'.format(entry))
    try:
        page = wiki.page(entry)
    except wiki.exceptions.DisambiguationError as e:
        userinput = ''
        while userinput not in e.options or userinput=='':
            print(e.options)
            userinput = input('Please specify \'{}\'. Choose from the options above.\n '.format(entry))
        search_in_wiki(userinput)
        return
    except wiki.exceptions.PageError as e:
        print('{} does not match any pages. Skipping this entry.'.format(entry.upper()))
        return

    search_results.append({
        'title':    unidecode(page.title if (' (' not in page.title) else page.title[:page.title.find(' (')]),
        'link_id':  unidecode(page.title),
        'summary':  unidecode(page.summary),
        'content':  unidecode(page.content),
        'links':    [unidecode(link) for link in page.links],
        'rev_id':   page.revision_id,
        'accessed': now
    })
    new_title = search_results[-1]['title']
    new_finds.append(new_title)
    df_rels[new_title], df_rels.loc[new_title] = None, None


def find_relationship(base_page, search_results, depth=0, rel_path=[]):
    """
    Search all other pages to see if they mention the base page. Begins by
    searching for the base page is in the other page's links, then
    searches for the base page in the content body.
    
    If no links are found, then each link in the base page will be searched using
    the same methodology above.

    Returns an array (agg_content) containing found content from each of the
    other pages.

    depth = degrees of separation between each page; direct link = 0\n
    rel = array of each "path" from the base to target page (min depth)\n
    text = array of the text where pages are mentioned in each path
    """
    global agg_content, found_content
    agg_content = []
    search_key = base_page['title']
    search_link = base_page['link_id']

    for target_page in [j for j in search_results if j['title']!=search_key]:        # can move this line to main()? (low prio)
        print('Searching for {} in {}...'.format(search_key, target_page['title']))
        if depth==0:
            rel_path = []
            found_content = {       # could turn this into a Class? (low prio)
                'depth': depth,
                'rel'  : [],
                'text' : []
            }
        rel_path.append(search_key)
        
        if search_link in target_page['links']:
            rel_path.append(target_page['title'])
            found_content['rel'].append(rel_path)
            found_content['text'].append([])

            for i, item in enumerate(rel_path[:-1]):      # content "snake" search for all entries in the rel_path
                next_item = rel_path[i+1]
                target_page = [j for j in search_results if j['title']==next_item][0]
                search_in_content(item, target_page)
                df_rels.at[item, next_item] = len(found_content['text'][-1][-1])

            agg_content.append(found_content)
            if depth>0: return
        else:
            search_in_links(base_page, target_page, depth+1, rel_path)

    return agg_content

def search_in_content(search_key, target_page):
    """
    Search for the sentences in the other page where the base page is mentioned.
    Appends results to found_content['text']
    """
    found_content['text'][-1].append(
        [hit.strip() for hit in 
            re.findall((r"([^.\n]*?" + search_key + r"[^.$\n]*\.)"),
            target_page['content'], re.IGNORECASE)
        ])   # doesn't return as many results for some reason??

def search_in_links(base_page, target_page, depth, rel_path):
    """
    Search for matching pages between base and target pages. Runs find_relationship()
    for each match. Otherwise, search base page's links further until a match with
    the target page is found.
    """
    link_match = set(base_page['links']) & set(target_page['links'])
    current_link_search = []
    if link_match:
        found_content['depth'] = depth
        print('Match found. Searching for ' + str(len(link_match)) + ' links in Wiki.')
        for entry in link_match:
            search_in_wiki(entry)           # MAJOR EDIT: now appends to search_results instead of link_
            current_link_search.append(search_results[-1])

    else:
        depth += 1
        print('Match not found. Searching Wiki for all links in ' + base_page['title'])
        for entry in base_page['links']:
            search_in_wiki(entry)           # MAJOR EDIT: same here
            current_link_search.append(search_results[-1])

    [search_in_links(entry, [target_page], depth, rel_path) for entry in current_link_search]   #link_search_results if it doesn't work


def write_to_files():
    """
    Prints search results to csv, json, and text. Updates search_archive.json with
    new_entries for future use.
    """
    df_rels.fillna(0, inplace=True)
    df_rels.to_csv('results/{}_rel.csv'.format(FILENAME))

    with open('results/{}.json'.format(FILENAME), 'w+') as savefile:
        json.dump(json.dumps(write_to_file), savefile)

    with open('results/{}.txt'.format(FILENAME),'w+') as f:
        f.write('DATE OF UDPATE: {}\nSEARCH QUERY: {}\n\n'.format(now, search_query))
        for base_page in write_to_file:
            f.write(base_page['id'].upper() + '\n')
            for other_page in base_page['content']:
                for rel in other_page['rel']:
                        f.write('{} - {} degrees\n'.format(rel[-1], other_page['depth']))
                        if len(rel)>2: f.write('RELATIONSHIP: ' + str(rel))
                    
                for text in other_page['text']:
                        for subtext in text:
                            f.write('HITS: ' + str(len(subtext)) + '\n')
                            for hit in subtext:
                                f.write('{}\n'.format(hit))
            f.write('\n\n')

    with open('results/search_archive.json', 'r+') as f:
        try:
            archive = json.loads(json.load(f))      # loads and dumps as string
        except json.decoder.JSONDecodeError:
            archive = []
        [search_results.append(saved_entry)
            for saved_entry in archive
            if saved_entry['title'] not in [page['id'] for page in write_to_file]]
        f.seek(0)
        f.truncate()    # clear file
        json.dump(json.dumps(search_results), f)

    print('{} entries added to search archive. All results written to files.'.format(len(new_finds)))

main()