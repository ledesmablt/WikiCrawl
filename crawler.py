import wikipedia as wiki
import pandas as pd
import json
import re
from datetime import date, datetime, timedelta
from unidecode import unidecode
from copy import copy


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
        initial_search = copy(search_results)
        print('Data collection completed.') 

    [write_to_file.append({
            'id':page['title'],
            'content':find_relationship(page, initial_search)
        }) for page in initial_search]
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

def search_in_wiki(entry):
    """
    Searches Wikipedia and search_archive.json (if applicable) based on user query.
    Appends results to search_results array. New queries are added to the new_finds array,
    later to be added to search_archive.json.
    """
    try:
        for session_entry in search_results:
            if entry.lower() in session_entry['title'].lower():
                print(entry + ' exists in current session.')
                return
    except: pass

    try:
        for saved_entry in archive:
            if entry.lower() in saved_entry['title'].lower():
                print(entry + ' found in saved file.')
                search_results.append(saved_entry)
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
        'rev_id':   page.revision_id,
        'accessed': now
    })

    search_results[-1]['links'] = list(set(
        [link for link in page.links
        if link in search_results[-1]['content']
        or link[:link.find(' (')] in search_results[-1]['content']] # the ' (' often isn't in the body
    ))
    
    new_title = search_results[-1]['title']
    new_finds.append(new_title)
    df_rels[new_title], df_rels.loc[new_title] = None, None


def find_relationship(base_page, search_request, depth=0, rel_path=[]):
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
    if depth==0: agg_content = []
    search_key = base_page['title']

    for target_page in [j for j in search_request if j['title']!=search_key]:        # can move this line to main()? (low prio)
        print('Searching for {} in {}...'.format(search_key, target_page['title']))
        if depth==0:
            rel_path = []
            found_content = {
                'depth': depth,
                'rel'  : [],
                'text' : []
            }
        rel_path.append(search_key)

        if (search_key in target_page['content']) or (target_page['title'] in base_page['content']):
            rel_path.append(target_page['title'])
            found_content['rel'].append(copy(rel_path))
            found_content['text'].append([])

            for i, item in enumerate(rel_path[:-1]):      # content "snake" search for all entries in the rel_path
                next_item = rel_path[i+1]
                target_page = [page for page in search_results if page['title']==next_item][0]
                found_content['text'][-1].append(search_in_content(item, target_page))
                df_rels.at[item, next_item] = len(found_content['text'][-1][-1])
                df_rels.at[next_item, item] = len(found_content['text'][-1][-1])

            rel_path.pop(); rel_path.pop()
            if found_content not in agg_content:    # solves double-saving problem
                agg_content.append(found_content)

        elif depth<=1:    # limit depth to 1 to avoid oversearch
            print('No direct match found. Searching in links.\n')
            search_in_links(base_page, target_page, depth+1, rel_path)

        else:
            print('Content not found. Skipping entry.')
            rel_path.pop()

    if depth==0: return agg_content

def search_in_content(search_key, target_page, backwards_search=False):
    """
    Search for the sentences in the other page where the base page is mentioned.
    Returns a list containing the sentences.
    If no data is found initially, does a 'reverse search' by flipping the search and target page.
    """
    found_text = [hit.strip() for hit in 
            re.findall((r"([^.\n]*?" + search_key + r"[^.$\n]*\.)"),
            target_page['content'], re.IGNORECASE)]
    
    if backwards_search: return found_text
    if not found_text:
        (search_key, target_page) = (
            target_page['title'], [page for page in search_results if search_key==page['title']][0]
        )
        found_text = search_in_content(search_key, target_page, True)

    return found_text

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
            search_in_wiki(entry)
            try:
                newest_entry = [page for page in search_results if page['link_id']==entry][0]
                current_link_search.append(newest_entry)
            except: pass #search_results.pop()

    else:
        depth += 1
        print('Match not found. Searching Wiki for all links in ' + base_page['title'])
        for entry in base_page['links']:
            search_in_wiki(entry)
            try:
                newest_entry = [page for page in search_results if page['link_id']==entry][0]
                current_link_search.append(newest_entry)
            except: pass #search_results.pop()

    [find_relationship(entry, [target_page], depth, rel_path) for entry in current_link_search]


def write_to_files():
    """
    Prints search results to csv, json, and text. Updates search_archive.json with
    new_entries for future use.
    """
    df_rels.fillna(0, inplace=True)
    df_rels.to_csv('results/{}_rel.csv'.format(FILENAME), index_label='index')

    with open('results/{}.json'.format(FILENAME), 'w+') as savefile:
        json.dump(json.dumps(write_to_file), savefile)

    with open('results/{}.txt'.format(FILENAME),'w+') as f:
        f.write('DATE OF UDPATE: {}\nSEARCH QUERY: {}\n\n'.format(now, search_query))
        for base_page in write_to_file:
            f.write(base_page['id'].upper())
            for other_page in base_page['content']:
                for item_ind in range(0, len(other_page['rel'])):
                    rel = other_page['rel'][item_ind]
                    f.write('\n' + str(rel) + '\n') if len(rel)>2 else f.write('\n')
                    for i, subtext in enumerate(other_page['text'][item_ind]):
                        f.write('{} -- {} hit/s\n'.format(rel[i+1], str(len(subtext))))
                        for hit in subtext:
                            f.write('> {}\n'.format(hit))
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