import requests
from bs4 import BeautifulSoup
import re
import datetime
import json

url = "https://www.nacc.gov.au/news-and-media"
suffix = "?page=0"
targets = []

def get_target_links(url=url, suffix=suffix):
    # Fetch the webpage content
    response = requests.get(url + suffix)
    html_content = response.content

    # Parse the HTML content with BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")

    # Find all links
    links = soup.find_all("a")

    # Find links to update posts
    for link in links:
        if link.text.strip() and (link.text.strip() == "Update: referrals, assessment and investigations" or link.text.strip() == "Update: 100 days of the National Anti-Corruption Commission"):
            targets.append(link.get("href"))

    # Check if there is a next page (look in links)
    for link in links:
        if link.text.strip() and link.text.strip() == "Next page\nNext":
            suffix = link.get("href")
            get_target_links(url, suffix)
            

def main():
    get_target_links()

    results = {}

    # Fetch each target page
    for target in targets:
        response = requests.get(target)
        html_content = response.content

        soup = BeautifulSoup(html_content, "html.parser")
        text = soup.get_text()

        # find the date in format "%w %B %Y"
        date = re.search(r"\d{1,2} \w+ \d{4}(?=, the Commission received)", text)
        if not date and re.search(r"Update: 100 days of the National Anti-Corruption Commission", text):
            date = "9 October 2023"
        else:
            date = date.group()

        # convert to datetime object
        date = datetime.datetime.strptime(date, "%d %B %Y").date()

        # find the number of referrals "the Commission received X referrals"
        referrals = re.search(r"(?<=the Commission received )\d+(?= referrals)", text.replace(",", ""))
        if referrals:
            referrals = int(referrals.group())
        else:
            referrals = -1
        
        # find the number of excluded referrals "X referrals have been excluded at the triage stage"
        excluded = re.search(r"\d+(?= referrals have been excluded at the triage stage)", text.replace(",", ""))
        if excluded:
            excluded = int(excluded.group())
        else:
            excluded = -1
        
        # find the number of referrals pending triage "X referrals are pending triage."
        pending = re.search(r"\d+(?= referrals)", text.replace(",", ""))
        if pending:
            pending = int(pending.group())
        else:
            pending = -1
        
        # find the number of referrals in active triage "X referrals are currently in active triage."
        active = re.search(r"\d+(?= referrals are currently in active triage)", text.replace(",", ""))
        if active:
            active = int(active.group())
        else:
            active = -1
        
        # find the number of referrals under assessment "X referrals are currently under assessment."
        assessment = re.search(r"\d+(?= referrals are currently under assessment)", text.replace(",", ""))
        if not assessment:
            assessment = re.search(r"\d+(?= referrals which have been triaged are currently under assessment)", text.replace(",", ""))
        if not assessment:
            assessment = re.search(r"\d+(?= referrals are currently under the second stage of assessment)", text.replace(",", ""))
        if assessment:
            assessment = int(assessment.group())
        else:
            assessment = -1
    
        # preliminary investigations
        preliminary = re.search(r"\d+(?= preliminary investigations)", text.replace(",", ""))
        if not preliminary:
            preliminary = re.search(r"(?<=The number of preliminary investigations remains at )\d+", text.replace(",", ""))
        if preliminary:
            preliminary = int(preliminary.group())
        else:
            preliminary = -1

        # new investigations
        new = re.search(r"\d+(?= new investigations)", text.replace(",", ""))
        if not new:
            new = re.search(r"(?<=To date the Commission has opened )\d+(?= investigations)", text.replace(",", ""))
        if not new:
            new = re.search(r"(?<=The Commission has opened )\d+(?= investigations)", text.replace(",", ""))
        if new:
            new = int(new.group())
        else:
            new = -1

        # referred to other agencies
        referred = re.search(r"(?<=referred )\d+(?= corruption issues)", text.replace(",", ""))
        if not referred:
            if re.search(r"has referred one corruption issue", text) or re.search(r"refer one corruption issue", text):
                referred = 1
        if referred and referred != 1:
            referred = int(referred.group())
        elif referred != 1:
            referred = 0

        # inherited investigations
        inherited = re.search(r"\d+(?= active investigations inherited)", text.replace(",", ""))
        if inherited:
            inherited = int(inherited.group())
        else:
            inherited = -1

        # add to results
        results[date.strftime("%Y-%m-%d")] = {
            "referrals": referrals,
            "excluded_triage": excluded,
            "pending_triage": pending,
            "active_triage": active,
            "assessment": assessment,
            "preliminary_investigation": preliminary,
            "new_investigation": new,
            "inherited_investigation": inherited,
            "referred": referred,
            "url": target
        }

    # Save to JSON
    with open("data.json", "w") as outfile:
        json.dump(results, outfile, indent=4)

    # Save to CSV
    with open("data.csv", "w") as outfile:
        outfile.write("date,pending_triage,active_triage,assessment,preliminary_investigation,new_investigation,inherited_investigation,referred\n")
        for date, data in sorted(results.items(), key=lambda x: datetime.datetime.strptime(x[0], "%Y-%m-%d")):
            outfile.write(f"{date},{data['referrals']},{data['excluded_triage']},{data['pending_triage']},{data['active_triage']},{data['assessment']},{data['preliminary_investigation']},{data['new_investigation']},{data['inherited_investigation']},{data['referred']}\n")

if __name__ == '__main__':
    main()