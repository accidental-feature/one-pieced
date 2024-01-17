import requests
from bs4 import BeautifulSoup, NavigableString
import re

class Arc:
	def __init__(self, title, summary):
		self.title = title
		self.summary = summary

class Saga:
	def __init__(self, title, arcs=None):
		self.title = title
		self.arcs = arcs if arcs else []

	def add_arc(self, arc):
		self.arcs.append(arc)
	
	def __str__(self):
		arc_str = ', '.join(arc.title for arc in self.arcs)
		return f"Saga: {self.title}, Arcs: [{arc_str}]"

class MainSaga:
	def __init__(self, title, sagas=None):
		self.title = title
		self.sagas = []

	def add_saga(self, saga):
		self.sagas.append(saga)
	
	def __str__(self):
		saga_str = ', '.join(str(saga) for saga in self.sagas)
		return f"MainSaga: {self.title}, Sagas: [{saga_str}]"

def is_main_saga_row(row):
	# Check if the row has a 'th' tag with the specific style
	return bool(row.find('th', style="background:#DADADA;"))

def get_main_saga_title(row):
	return row.find('a').text.strip()

def is_saga_row(row):
	# Check if any 'td' tag with 'colspan="5"' or 'colspan="6"' within the row contains a 'b' tag
	td_tags = row.find_all('td', {'colspan': ['5', '6']})
	return any(td.find('b') for td in td_tags)

def get_saga_title(row):
	return row.find('a').text.strip()

def is_arc_row(row):
	# Similar to Sub-Saga rows but checks for the absence of 'b' tag
	return bool(row.find('td', {'colspan': ['5', '6']}) and not row.find('b'))

def get_arc_title(td):
	arc_link = td.find('a')
	if arc_link:
		return arc_link.text.strip()
	return "Unknown Arc"

def get_arc_url(row):
	arc_link = row.find('a')
	if arc_link and 'href' in arc_link.attrs:
		return 'https://onepiece.fandom.com' + arc_link['href']
	return None

# Process a paragraph to ensure proper spacing around <a> tags
def process_paragraph(para):
	paragraph_text = ''
	for content in para.children:
		if isinstance(content, NavigableString):
			paragraph_text += content
		elif content.name == 'a':
			# Add a leading space before the <a> tag text
			paragraph_text += ' ' + content.get_text()
	return paragraph_text.strip()

def get_arc_summary(html_content):
	soup = BeautifulSoup(html_content, 'html.parser')

	# Find the summary starting point
	summary_start = soup.find('span', id='Summary')
	if not summary_start:
		return "No summary found"

	summary_text = ""
	collect = False

	for sibling in summary_start.parent.next_siblings:
		if sibling.name == 'h2':
			if 'Story Impact' in sibling.get_text():
				break  # Stop if 'Story Impact' section is reached
		elif sibling.name == 'p':
			summary_text += '\n\n' + process_paragraph(sibling)
		elif sibling.name == 'h3':
			summary_text += '\n\n' + '#### ' + sibling.get_text(strip=True)

	cleaned_summary = re.sub(r'\s*\[\d+\]\s*', '', summary_text)
	return cleaned_summary.strip()

def print_table_structure(main_sagas):
	for main_saga in main_sagas:
		print(f"Main Saga: {main_saga.title}")
		for saga in main_saga.sagas:
			print(f"  Sub-Saga: {saga.title}")
			for arc in saga.arcs:
				print(f"    Arc: {arc.title}")
		print("\n")

def scrape_data():
	url = "https://onepiece.fandom.com/wiki/Chapters_and_Volumes"
	response = requests.get(url)
	soup = BeautifulSoup(response.content, 'html.parser')

	rows = soup.find_all('tr')

	main_sagas = []
	current_main_saga = None
	current_sagas = []

	for idx, row in enumerate(rows):
		if is_main_saga_row(row):
			if current_main_saga:
				for saga in current_sagas:
					current_main_saga.add_saga(saga)
				main_sagas.append(current_main_saga)
				current_sagas = []
			current_main_saga = MainSaga(title=get_main_saga_title(row))

		elif is_saga_row(row):
			td_tags = row.find_all('td', {'colspan': ['5', '6']})
			for td in td_tags:
				if td.find('b'):
					saga_title = td.find('a').text.strip()
					current_sagas.append(Saga(title=saga_title))

		elif current_sagas:
			td_tags = row.find_all('td', {'colspan': ['5', '6']})
			for td_index, td in enumerate(td_tags):
				if not td.find('b'):  # This is an arc
					arc_url = get_arc_url(td)
					arc_title = get_arc_title(td)
					if arc_title == "Unknown Arc":
						continue
					arc_summary = ""
					if arc_url:
						arc_response = requests.get(arc_url)
						if arc_response.status_code == 200:
							arc_summary = get_arc_summary(arc_response.content)
					arc = Arc(title=arc_title, summary=arc_summary)
					if td_index < len(current_sagas):
						current_sagas[td_index].add_arc(arc)

	# Add the last set of sagas to the last main saga
	if current_sagas:
		for saga in current_sagas:
			current_main_saga.add_saga(saga)
	# Add the last main saga to the list
	if current_main_saga:
		main_sagas.append(current_main_saga)

	for main_saga in main_sagas:
		filename = './docs/SuperRookies.md' if 'Super Rookies' in main_saga.title else './docs/NewWorld.md'
		with open(filename, 'w', encoding='utf-8') as md_file:
			md_file.write(f'# __{main_saga.title}__\n')  # h1 tag for main saga title
			for sub_saga in main_saga.sagas:
				md_file.write(f'\n## {sub_saga.title}\n')  # h2 tag for sub-saga title
				for arc in sub_saga.arcs:
					md_file.write(f'\n### __{arc.title}__\n\n')  # List item for each arc
					md_file.write(f'{arc.summary}\n')  # Arc summary as a nested list item

	print("Markdown files have been created.")
	return main_sagas

scrape_data();