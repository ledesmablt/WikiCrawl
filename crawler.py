import wikipedia as wiki
import json
from datetime import datetime, timedelta
from unidecode import unidecode
from bs4 import BeautifulSoup

now = datetime.now()
userinput = ''
search_query, search_results, write_to_file = [],[],[]


def user_input_search():
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

def search_in_wiki(entry, search_results=search_results, userinput=''):
    print('Collecting data for {}...'.format(entry))
    try:
        page = wiki.page(entry)
    except wiki.exceptions.DisambiguationError as e:
        while userinput not in e.options:
            print(e.options)
            userinput = input('Please specify \'{}\'. Choose from the options above.\n '.format(entry))
        search_in_wiki(userinput)
    except wiki.exceptions.PageError as e:
        print('{} does not match any pages. Skipping this entry.'.format(entry.upper()))
        return
    
    search_results.append({
        'title':    unidecode(page.title),
        'summary':  unidecode(page.summary),
        'content':  unidecode(page.content),
        'links':    set([unidecode(link) for link in page.links]),         # returns list
        'rev_id':   page.revision_id,   # to see if it's been updated since last time
        'accessed': now
    })

def find_relationship(current_page, search_results, depth=0, rel=[]):
    global aggregated_content, found_content
    aggregated_content = []
    search_key = current_page['title']

    for other_page in [j for j in search_results if j['title']!=search_key]:
        print('Searching for', search_key, 'in', other_page['title'])
        relationship = [search_key, other_page['title']]
        found_content = {
            'depth': [depth, relationship],
            'text' : []
        }
        
        if search_key in other_page['links']:
            search_in_content(search_key, other_page, other_page['content'])
        else:
            search_in_links(current_page, other_page)

        aggregated_content.append(found_content)
    
    return aggregated_content

def search_in_content(search_key, other_page, content):
    if search_key in content:
        loc = content.find(search_key)
        text_beginning = loc-100 if loc-100 > 0 else 0          # need to format this to SENTENCE only
        containing_text = content[text_beginning:loc+100]
        found_content['text'].append((loc, containing_text))
        search_in_content(search_key, other_page, content[loc+1:])

# work in progress - having trouble with recursion
def search_in_links(base_page, target_page, depth=1):
    link_match = base_page['links'] & target_page['links']  # works like search_query
    if link_match:
        link_results = []   # works like search_results
        found_content['depth'][0] = depth
        found_content['depth'][1].insert(-1, base_page['title'])
        for entry in link_match:
            search_in_wiki(entry, link_results)
        for entry in link_results:
            find_relationship(entry, [target_page['name']], depth,
                              found_content['depth'][1]) # update current relationship
    else:
        print("scour each link on each page")


user_input_search()

for entry in search_query:
    search_in_wiki(entry)

print('Data collection completed.') 

for page in search_results:
    _page = {'id':page['title'], 'content':find_relationship(page, search_results)}
    write_to_file.append(_page)



# write to files
with open('results/results.txt','r+') as f:
    f.write('DATE OF UDPATE: {}\nSEARCH QUERY: {}\n\n'.format(now, search_query))
    for base_page in write_to_file:
        f.write(base_page['id'].upper() + '\n')
        for other_page in base_page['content']:
            f.write('DEPTH: {} degrees - {}\n'.format(other_page['depth'][0], other_page['depth'][1]))
            f.write('HITS: ' + str(len(other_page['text'])) + '\n')
            for hit in other_page['text']:
                f.write('{} - {}\n'.format(hit[0], hit[1]))
        f.write('\n\n')

with open('results/data.json', 'r+') as savefile:   #read and write
    # import old data
    # update old data with new if applicable
    json.dump(write_to_file, savefile)

print('Search for relationships complete. Results written to files.')
exit
