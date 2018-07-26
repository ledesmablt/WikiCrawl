# WikiCrawl
Find relationships between Wikipedia pages.

What it does:
- shows how pages mention each other in content
- saves results to .txt and .json

I'm fairly new to programming in general (this is my first actual project), so any suggestions for code/algorithm improvements are very welcome!

Planned improvements:
- reduce output text to the sentence containing the mentioned page
- search queries "saved" in JSON can be imported to avoid redundant searches
- return frequently mentioned keywords
- in-depth search via scouring links for related content (need a solid search algorithm for this)
- visualized network of page interrelationships
  - "strongly linked" pages (those that have multiple mentions) will have thicker lines in the web
