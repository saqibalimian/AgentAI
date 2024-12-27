from fastapi import FastAPI, HTTPException
import requests
from typing import List
from serpapi import GoogleSearch
import json 
import os
import datetime
from bs4 import BeautifulSoup
import demoji
import sys
import traceback
import re
app = FastAPI()
from typing import List, Dict, Optional
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field
import streamlit as st
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class DISCAttribute(BaseModel):
    score: int = Field(..., ge=0, le=100, description="Score for the DISC attribute (0-100)")
    traits: List[str] = Field(..., description="List of traits associated with the attribute")
    behavioral_indicators: str = Field(..., description="Behavioral indicators inferred for the attribute")

class DISCOutput(BaseModel):
    dominance: DISCAttribute
    influence: DISCAttribute
    steadiness: DISCAttribute
    conscientiousness: DISCAttribute

class DISCAnalysisSchema(BaseModel):
    input: str = Field(..., description="Profile description from LinkedIn")
    output: DISCOutput 
    name:str = Field(..., description="Name of the person")

DISC_instruction  = """You are a DISC psychometric analysis generator. Your role is to analyze a person's LinkedIn profile data and create a detailed DISC profile based on the four DISC personality dimensions: Dominance (D), Influence (I), Steadiness (S), and Conscientiousness (C).

Instructions:
Analyze LinkedIn Data: Extract relevant insights from the provided LinkedIn profile data, including job titles, professional summaries, achievements, skills, endorsements, activity, and other publicly available information.
{person_profile}
Derive DISC Traits:
Use role descriptions and achievements to infer behavioral tendencies for each DISC dimension.
For example, leadership roles may indicate high Dominance, while customer-facing roles might suggest high Influence.
Generate Scores: Assign a score (0-100) for each DISC dimension based on inferred behaviors and priorities.
Identify Personality Type: Determine the primary and secondary DISC types and provide a concise summary of the personality.
Provide Insights: Generate insights and recommendations tailored to professional contexts, such as ideal roles, strengths, challenges, and effective collaboration strategies.

"""
CACHE_FILE = "search_cache.json"

# Load cache from file if it exists
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r") as f:
        cache = json.load(f)
else:
    cache = {}

@app.get("/google_search")
def google_search(query: str):
    try:
        params = {
            "engine": "google",
            "q": query +'" site:linkedin.com/in/',
            "api_key": "136f37d06a4581f56e44549ba18ff6d650a3155a7f73335aeae71f843919763f"
        }
        if query in cache:
            results = cache[query]
        else:
            search = GoogleSearch(params)
            results = search.get_dict()
            cache[query] = results
            # Save the cache to the file
            with open(CACHE_FILE, "w") as f:
                json.dump(cache, f)

         # Extract the organic_results list
        organic_results = results.get("organic_results", [])

        # Parse the results to extract desired fields
        extracted_data = []
        for item in organic_results:
            name = item.get("title", "")  # Assuming 'name' corresponds to 'title'
            link = item.get("link", "")
            snippet = item.get("snippet", "")
            # Extract location from the rich_snippet if it exists
            location = item.get("rich_snippet", {}).get("top", {}).get("extensions", [])[0] if item.get(
                "rich_snippet", {}).get(
                "top", {}).get("extensions") else ""

            # Append the parsed data to the list
            extracted_data.append({
                "name": name,
                "link": link,
                "location": location,
                "snippet": snippet
            })
        linkedin_person =[]
        for entry in extracted_data[:1]:
            link = entry["link"]
            linkedin_person.append(linkedInScrapper(link))

        disc =  discGenerator(linkedin_person)
        return {
            "Profile":linkedin_person,
            "disc": disc
               }       #return linkedin_person
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        
        raise HTTPException(status_code=500, detail=str(e) + str(repr(traceback.format_exception(exc_type, exc_value, exc_traceback))))
    
def discGenerator(linkedin_person):
    try:
        llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key='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')
        structured_llm = llm.with_structured_output(DISCOutput)
        
        # Generate question
        system_message = DISC_instruction.format(person_profile=linkedin_person)
        person_disc = structured_llm.invoke([SystemMessage(content=system_message)])
       
       
        
        print(person_disc)
        return {"person": person_disc}
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        raise HTTPException(status_code=500, detail=str(e) + str(repr(traceback.format_exception(exc_type, exc_value, exc_traceback))))

def linkedInScrapper(linkedin_profile_url):
      
    if linkedin_profile_url[-1] == '/':
        linkedin_username = linkedin_profile_url.split('/')[-2]
    else:
        linkedin_username = linkedin_profile_url.split('/')[-1]

    iscraper_data = {
        "profile_id": linkedin_username,
        "profile_type": "personal",
        "contact_info": True,
        "bypass_cache": True,
        "recommendations": False,
        "related_profiles": False,
        "network_info": False
    }

    iscraper_data["include_profile_image"] = True

    api_endpoint = 'https://api.proapis.com/iscraper/v4/profile-details'
    api_key = 'BAYibUccYFuR7mqgzgJhkma4ZU1o2vuR'

    headers = {'X-API-KEY': api_key}

    url = api_endpoint
    response = requests.post(url, headers=headers, json=iscraper_data)
    if response.status_code == 200:
        linkedin_profile_json = response.json()
        result = extract_profile_details(linkedin_profile_json)
       # result = parse_iscraper_linkedin_profile(linkedin_profile_json)
    return result


def extract_profile_details(parsed_data):
    full_name = f"{parsed_data.get('first_name', '')} {parsed_data.get('last_name', '')}".strip()
    profile_picture = parsed_data.get('profile_picture', None).strip()
    urn = parsed_data.get('entity_urn', None).strip()
    sub_title = parsed_data.get('sub_title', None).strip()

    link = f"https://www.linkedin.com/in/{urn.replace('urn:li:fsd_profile:', '')}" if urn else ""



    overview = parsed_data.get('overview', '')
    designation = parsed_data.get('designation', '')
    education = parsed_data.get('education', '')
    experience = parsed_data.get('position_groups', '')
    company_name = parsed_data.get('es_data', {}).get('company_name', '')
    linkedin_company_id = parsed_data.get('linkedin_company_id', '')
    skills = parsed_data.get('skills', '')

    location = parsed_data.get('location', '')
    twitter = parsed_data.get('twitters', [])
    experience = parse_experience(experience)
    return {
        "name": full_name,
        "picture": profile_picture,
        "urn": urn,
        "headline": sub_title,
        "link": link,
        "overview": str(overview).strip() if overview else '',
        "designation": designation,
        "education": str(education).strip() if education else '',
        "companyname": company_name.strip() if company_name else '',
       # "location": location.strip() if location else '',
        "twitters": twitter if len(twitter) else [],
        "experience": str(experience) if experience else '',
        "skills" :skills
    }

def parse_experience(experience_data):
    """
    Parse the experience data into a structured format.
    """
    experiences = []
    for exp in experience_data:
        company = exp.get('company', {})
        date = exp.get('date', {})
        profile_positions = exp.get('profile_positions', [])

        parsed_experience = {
            "company": {
                "id": company.get('id'),
                "name": company.get('name'),
                "logo": company.get('logo'),
                "url": company.get('url'),
                "employees": company.get('employees')
            },
            "date": {
                "start": date.get('start'),
                "end": date.get('end')
            },
            "profile_positions": []
        }

        for position in profile_positions:
            parsed_position = {
                "location": position.get('location'),
                "date": position.get('date'),
                "company": position.get('company'),
               # "description": position.get('description'),
                "title": position.get('title'),
                "employment_type": position.get('employment_type')
            }
            parsed_experience["profile_positions"].append(parsed_position)

        experiences.append(parsed_experience)

    return experiences
def convert_month_to_string(month):
    dummy_date = datetime.strptime(str(month), '%m')
    return dummy_date.strftime('%b')

def extractIscraperDetailAccomplishment(key, value):
    """
    This function is used to extract all the detail of Accomplishments portion of linkedin. This is basically part of
    formatting of nubela api to our parsers' format
    params key: it is the key of all accomplishment types in the dictionary of nubela api
    params value: value of all accomplishment types in the dictionary of nubela api
    return object_dict: dictionry contains the details of accomplishment
    """
    object_dict = {}
    try:
        if 'courses' == key:
            object_dict = {'name': 'Courses', 'Details': []}
            for val in value:
                object_dict['Details'].append({'Course': val['name']})

            return object_dict

    except Exception as e:
        print("")

    try:
        if 'publications' == key:
            temp_list = []
            object_dict = {'name': 'Publications'}
            for val in value:
                temp_dict = {}
                temp_dict['title'] = ""
                temp_dict['date'] = ""
                temp_dict['publisher'] = ""
                temp_dict['description'] = ""
                temp_dict['link'] = ""
                temp_list.append(temp_dict)
            object_dict['Details'] = temp_list
            return object_dict
    except Exception as e:
        print("")

    try:
        if 'languages' == key:
            languages = value.get('profile_languages', [])
            if not languages:
                object_dict['Details'] = []
                return object_dict

            object_dict = {'name': 'Languages', 'Details': []}
            for val in languages:
                dic = {'title': val.get('name', ''), 'proficency': val.get('proficiency', '')}
                object_dict['Details'].append(dic)

            return object_dict
    except Exception as e:
        print("")

    try:
        if 'projects' == key:
            object_dict = {'name': 'Projects', 'Details': []}
            for val in value:
                title = val.get('title', '')
                description = val.get('description', '')
                url = val.get('url', '')
                try:
                    start_month = val.get('date', {}).get('start', {}).get('month', '')
                    start_year = val.get('date', {}).get('start', {}).get('year', '')
                    start_date = datetime.strptime(str(start_month), "%m").strftime("%b") + ' ' + str(start_year)
                except:
                    start_date = ''
                try:
                    end_month = val.get('date', {}).get('end', {}).get('month', '')
                    end_year = val.get('date', {}).get('end', {}).get('year', '')
                    end_date = datetime.strptime(str(end_month), "%m").strftime("%b") + ' ' + str(end_year)
                except:
                    end_date = ''

                if not start_date and not end_date:
                    date = ''
                else:
                    date = f'{start_date} - {end_date}'

                dic = {'title': title, 'description': description, 'link': url, 'date': date}
                object_dict['Details'].append(dic)

            return object_dict

    except Exception as e:
        print("")

    try:
        if 'awards' == key:
            object_dict = {'name': 'Honors & Awards', 'Details': []}
            for val in value:
                title = val.get('title', '')
                issuer = val.get('issuer', '')
                description = val.get('description', '')
                month = val.get('date', {}).get('month', '')
                year = val.get('date', {}).get('year', '')
                date = ''
                if month:
                    date = datetime.strptime(str(month), "%m").strftime("%b") + ' ' + str(year)

                dic = {'title': title, 'issuer': issuer, 'description': description, 'date': date}
                object_dict['Details'].append(dic)

            return object_dict

    except Exception as e:
        print("")

def get_duration(date):
    time = ''
    if date['month']:
        time = convert_month_to_string(date.get('month', '')) + ' '
    if date['year']:
        if time:
            time += str(date['year'])
        else:
            time = str(date['year'])
    return time
def convert_data_to_string(input_data):
    volunteer_work = ''
    try:
        start_time = ''
        end_time = ''
        if input_data:
            for entry in input_data:
                role = entry.get('role', '')
                if role:
                    volunteer_work += role.strip() + '\r\n'

                if entry['date']['start']:
                    start_time = get_duration(entry['date']['start'])

                if entry['date']['end']:
                    end_time = get_duration(entry['date']['end'])

                if start_time and end_time:
                    volunteer_work += start_time.strip() + " - " + end_time.strip() + '\r\n'
                elif start_time:
                    volunteer_work += start_time.strip() + '\r\n'
                elif end_time:
                    volunteer_work += end_time.strip() + '\r\n'

                description = entry.get('description', '')
                if description:
                    volunteer_work += description.strip() + '\r\n'

                if volunteer_work:
                    volunteer_work += '\r\n'

        return volunteer_work
    except:
        return volunteer_work
def parse_iscraper_linkedin_profile(data):
    result = {}
   
    result['picture'] = data.get('profile_picture', '')
    if not result['picture']:
        result['picture'] = ''

    # volunteer_work
    volunteer_work = ''
    if data.get('volunteer_experiences', ''):
        volunteer_work = convert_data_to_string(data['volunteer_experiences'])
       
    result['volunteer_work'] = volunteer_work

    # accomplishments
    result['accomplishments'] = []

    # ['awards', 'patents', 'courses_taken', 'projects', 'languages', 'memberships']
    for key, value in data.items():
        try:
            if key in ['awards', 'courses', 'projects', 'languages', 'publications', 'certifications',
                       'patents'] and value is not None and len(value):
                if 'courses' == key:
                    title = 'Courses_taken'
                else:
                    title = key.capitalize()

                count = str(len(value))
                dic = {'title': title.encode(), 'count': count.encode(), 'list': []}

                # just for languages
                if key == 'languages':
                    languages = data.get('languages', {}).get('profile_languages', [])
                    if not languages:
                        continue

                    lang_dic = {'title': title.encode(), 'count': str(len(languages)).encode(), 'list': []}
                    for l in languages:
                        lang_dic['list'].append(l['name'])
                    result['accomplishments'].append(lang_dic)

                    continue

                # for other keys
                for k in value:
                    if 'title' in k:
                        dic['list'].append(k['title'])
                    elif 'name' in k:
                        dic['list'].append(k['name'])

                result['accomplishments'].append(dic)
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
          

    # detail_accomplishments
    result['detail_accomplishments'] = []
    for key, value in data.items():
        try:
            if key in ['awards', 'courses', 'projects', 'languages', 'publications', 'certifications',
                       'patents'] and value is not None and len(value):
                detailAccomplishment = extractIscraperDetailAccomplishment(key, value)
                if detailAccomplishment:
                    result['detail_accomplishments'].append(detailAccomplishment)
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()

    result['overview'] = ''
    if data.get('summary', ''):
        result['overview'] = "<div>\n\n" + data['summary'].replace("\n", "<br/>") + "\n\n\n<!-- --></div>"

    result['headline'] = data.get('sub_title', '')
    if not result['headline']:
        result['headline'] = ''

    result['skills'] = data.get('skills', [])

    twitter = []
    _twitter = data.get('contact_info', {})
    if _twitter:
        twitter = _twitter.get('twitter', [])
    if twitter: result['twitters'] = [twitter]

    result['location'] = data.get('location', {}).get('default', '')
    if not result['location']:
        result['location'] = ''
    full_name = data.get('first_name', '') + ' ' + data.get('last_name', '')
    api_full_name = data.get('full_name', '')

    try:
        full_name = demoji.replace(full_name, "").strip()
        api_full_name = demoji.replace(api_full_name, "").strip()
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
       

    if full_name:
        result['name'] = full_name
    elif api_full_name:
        result['name'] = api_full_name
    else:
        result['name'] = ''

    websites = []
    web = None
    _web = data.get('contact_info', {})
    if _web:
        web = _web.get('websites', [])
    if web:
        websites = [w['url'] for w in web]
    result['websites'] = websites

    result['ims'] = []
    result['phone'] = ""
    result['emails'] = []
    result[
        'bio'] = '<h2 class="pv-profile-section__card-heading Sans-21px-black-85%">Experience</h2><h2 class="pv-profile-section__card-heading Sans-21px-black-85%">Education</h2>'
    result['linkedin_company_id'] = ""

    # designation
    try:
        result['designation'] = data.get('position_groups')[0].get('profile_positions')[0].get('title', '')
        result['companyname'] = data.get('position_groups')[0].get('profile_positions')[0].get('company', '')
    except:
        result['designation'] = ''
        result['companyname'] = ''
    if not result['companyname']:
        result['companyname'] = ''
    if not result['designation']:
        result['designation'] = ''
    # getting eduction and schools data
    schools = []
    education = ''
    education_with_image = ''

    for edu in data.get('education', []):
        class_name = "pv-entity__logo-img pv-entity__logo-img EntityPhoto-square-4 lazy-image ember-view"

        try:
            edu_start_date = edu.get('date', {}).get('start', {}).get('year', '')
            edu_end_date = edu.get('date', {}).get('end', {}).get('year', '')
            if edu_start_date and not edu_end_date:
                edu_end_date = 'Present'
        except:
            edu_start_date = ''
            edu_end_date = ''

        if edu_start_date or edu_end_date:
            edu_date_string = f'{edu_start_date}</time> – <time>{edu_end_date}'
        else:
            edu_date_string = '</time><time>'

        school = edu.get('school', {}).get('name', '')
        degree = edu.get('degree_name', '')
        if not degree: degree = ''

        field_study = edu.get('field_of_study', '')
        if not field_study: field_study = ''

        school_logo = edu.get('school', {}).get('logo')
        if not school_logo:
            school_logo = 'https://s3-us-west-2.amazonaws.com/media.xiq.io/people2/icons/education.png'

        education += f'''
        <div>
            <div>
                <h3>{school}</h3>
                <p><span>{degree}</span></p>
                <p><span>{field_study}</span></p>
                <!---->
            </div>
            <p><span><time>{edu_date_string}</time></span></p>
        </div>
        '''

        education_with_image += f'''
        <div><img alt="{school}" class="{class_name}" loading="lazy" src="{school_logo}"/></div>
        <div>
            <div>
                <h3>{school}</h3>
                <p><span>{degree}</span></p>
                <p><span>{field_study}</span></p>
            </div>
            <p><span><time>{edu_date_string}</time></span></p>
        </div>
        '''

        # append school name to school list
        schools.append(school)

    result['schools'] = list(set(schools))
    #result['education'] = BeautifulSoup(education, 'html.parser')
   # result['education_with_image'] = BeautifulSoup(education_with_image, 'html.parser')

    # getting experience and companies data
    experience_with_image = ''
    experience = ''
    companies = []
    class_name = 'pv-entity__logo-img EntityPhoto-square-5 lazy-image ember-view'
    for exp in data.get('position_groups', []):
        for comp in exp.get('profile_positions', []):
            company_name = exp.get('company', {}).get('name')
            if not company_name:
                company_name = ''
            title = comp.get('title', '')

            location = comp.get('location', '')
            if not location: location = ''

            company_logo = exp.get('company', {}).get('logo', '')
            if not company_logo:
                company_logo = 'https://s3-us-west-2.amazonaws.com/media.xiq.io/people2/icons/defaultboards.png'

            try:
                start_month = comp.get('date', {}).get('start', {}).get('month', '')
                start_year = comp.get('date', {}).get('start', {}).get('year', '')
                if not start_month and start_year:
                    start_date = start_year
                else:
                    start_date = datetime.strptime(str(start_month), "%m").strftime("%b") + ' ' + str(start_year)
            except:
                start_date = 'Present'
                # exc_type, exc_value, exc_traceback = sys.exc_info()
                # logger.error(repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))

            try:
                end = comp.get('date', {}).get('end', {})
                if start_date and not end:
                    end_date = 'Present'
                elif not start_date:
                    end_date = ''
                else:
                    end_month = comp.get('date', {}).get('end', {}).get('month', '')
                    end_year = comp.get('date', {}).get('end', {}).get('year', '')
                    if not end_month and end_year:
                        end_date = end_year
                    else:
                        end_date = datetime.strptime(str(end_month), "%m").strftime("%b") + ' ' + str(end_year)
            except:
                end_date = 'Present'
                exc_type, exc_value, exc_traceback = sys.exc_info()
                # logger.error(repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))

            if start_date or end_date:
                date_string = f'{start_date} - {end_date}'
            else:
                date_string = ''

            experience += f'''
            <div>
                <h3>{title}</h3>
                <p>{company_name}<span></span></p>
                <div>
                    <h4><span>{date_string}</span></h4> 
                </div>
                <h4><span>{location}</span></h4>
            </div>
            '''

            experience_with_image += f'''
            <div><img alt="{company_name}" class="{class_name}" loading="lazy" src="{company_logo}"/></div>
            <div>
                <h3>{title}</h3>
                <p>{company_name}<span></span></p>
                <div>
                    <h4><span>{date_string}</span></h4>
                    <h4><span>{location}</span></h4>
                </div>
            </div>
            '''
            # append school name to school list
            companies.append(company_name)

    result['companies'] = list(set(companies))
    result['experience'] = BeautifulSoup(experience, 'html.parser')
    result['experience_with_image'] = BeautifulSoup(experience_with_image, 'html.parser')

    # content
    try:
        CLEANR = re.compile('<.*?>')
      #  combine_text = result['name'] + ' ' + result['overview'] + ' ' + str(result['experience']) + ' ' + str(
         #   result['education'])
        #combine_text = combine_text.replace('… see more', '')
       # cleantext = re.sub(CLEANR, '', combine_text)
       # result['content'] = ' '.join(cleantext.split())
    except:
        result['content'] = ''

    ### fields for PartialProfileStatus table
    #overview = data.get('summary', '')

  #  try:
 #       education = ' '.join(result['education'].text.split())
 #   except:
  #      education = ''
    try:
        experience = ' '.join(result['experience'].text.split())
    except:
        experience = ''

     
    
    return result


print (discGenerator("SAqib ali Director of engneering xiq "))