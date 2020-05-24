import json
import pathlib
import time
import traceback

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from datetime import datetime
CURRENT_DIR = pathlib.Path(__file__).parent.absolute()
config = {}
request_timeout = 30
csv_file_name = 'LinkedIn Profiles {}.csv'.format(datetime.now())
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36',
}

rejected_profiles = []

def save_to_excel(final_result):
    print('saving to excel')
    df = pd.DataFrame(final_result)
    df.to_csv(csv_file_name, encoding='utf-8', index=True)

    print('saved to : {}'.format(csv_file_name))


def init_config():
    print('initializing config')
    with open('{}/config.json'.format(CURRENT_DIR)) as json_file:
        data = json.load(json_file)

    config.update(data)

    config['headless'] = True if config.get('headless_mode', None) == 'Y' else False


def init_webdriver():
    options = Options()

    headless = config.get('headless', True)
    if headless:
        options.add_argument("--headless")

    driver = webdriver.Chrome(executable_path=config.get('chromedriver_path'), options=options)

    print('got driver')
    return driver


def scroll_slowly(driver, speed=8):
    current_scroll_position, new_height = 0, 1
    while current_scroll_position <= new_height:
        current_scroll_position += speed
        driver.execute_script("window.scrollTo(0, {});".format(current_scroll_position))
        new_height = driver.execute_script("return document.body.scrollHeight")


def get_link_details(profile_links, driver):
    print('get link details')

    result = []
    for link in profile_links:
        print('getting details of {}'.format(link))
        #link = 'https://www.linkedin.com/in/thomas-sandgaard-42b748/'
        # link = 'https://www.linkedin.com/in/danin-oldershaw/'
        #link = 'https://www.linkedin.com/in/martin-sandgaard-aa147b9b/'
        #link = 'https://www.linkedin.com/in/jaclyn-wittke-3b2036175/'
        #link = 'https://www.linkedin.com/in/marielleibovitz/'
        try:
            driver.get(link)
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, '//main[@class="core-rail"]')))

            #driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            scroll_slowly(driver)

            soup = BeautifulSoup(driver.page_source, 'lxml')

            candidate_name = soup.find('section', {'class': 'pv-top-card'}).find('li', {
                'class': 'inline t-24 t-black t-normal break-words'}).text.strip()

            current_position = soup.find('section', {'class': 'pv-top-card'}).find('h2').text.strip()

            location = soup.find('section', {'class': 'pv-top-card'}).find('li', {
                'class': 't-16 t-black t-normal inline-block'}).text.strip()

            candidate_dict = {
                'Candidate Name': candidate_name,
                'Current Position': current_position,
                'Location': location,
            }

            experience_section = soup.find('section', {'id': 'experience-section'}).find_all('section')[:3]

            for index, row in enumerate(experience_section):
                if row.find('li',{'class': 'pv-entity__position-group-role-item-fading-timeline'}):
                    #print('multiple  position')
                    position_group = row.find('li',{'class': 'pv-entity__position-group-role-item-fading-timeline'})
                    candidate_dict['Job {} Company'.format(index + 1)] = row.find('h3').text.split('Company Name')[-1].strip() if row.find('h3') else None
                    candidate_dict['Job {} Title'.format(index + 1)] = position_group.find('h3').text.split('Title')[-1].strip() if position_group.find('h3') else None
                    candidate_dict['Job {} Duration'.format(index + 1)] = row.find('h4').text.split('Total Duration')[-1].strip() if row.find('h4') else None
                elif row.find('li',{'class': 'pv-entity__position-group-role-item'}):
                    role_group = row.find('li',{'class': 'pv-entity__position-group-role-item'})
                    company_el = row.find('div', {'class': 'pv-entity__company-summary-info'})
                    candidate_dict['Job {} Company'.format(index + 1)] = company_el.find('h3').text.split('Company Name')[-1].strip() if company_el.find('h3') else None
                    candidate_dict['Job {} Title'.format(index + 1)] = role_group.find('h3').text.split('Title')[-1].strip() if role_group.find('h3') else None
                    candidate_dict['Job {} Duration'.format(index + 1)] = company_el.find('h4').text.split('Total Duration')[-1].strip() if company_el.find('h4') else None
                else:
                    #print('one position')
                    candidate_dict['Job {} Company'.format(index + 1)] = row.find('p', {'class':'pv-entity__secondary-title'}).text.strip() if row.find('p', {'class':'pv-entity__secondary-title'}) else None
                    candidate_dict['Job {} Title'.format(index + 1)] = row.find('h3').text.strip() if row.find('h3') else None
                    candidate_dict['Job {} Duration'.format(index + 1)] = row.find('h4',{'class': 'pv-entity__date-range'}).text.split('Dates Employed')[-1].strip() if row.find('h4',{'class': 'pv-entity__date-range'}) else None

                candidate_dict['Job {} Location'.format(index + 1)] = row.find('h4',{'class': 'pv-entity__location'}).text.split('Location')[-1].strip() if row.find('h4',{'class': 'pv-entity__location'}) else None

            candidate_dict['Link'] = link

            result.append(candidate_dict)
        except Exception as ex:
            rejected_profiles.append(link)
            print(ex)
            print('error for url: {}'.format(link))
    print("candidate result per page completed")

    return result


def get_page_result(url, driver):
    print("calling page {}".format(url))
    driver.get(url)
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="ember54"]')))

    #driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    #time.sleep(2)
    scroll_slowly(driver)

    profile_links = set([a_el.get_attribute('href') for a_el in
                         driver.find_elements_by_xpath("//div[@id='ember54']//a[contains(@href, '/in/')]")])

    page_results = get_link_details(profile_links, driver)

    return page_results


def linkedIn_scrape(driver):
    print('linkedin scraper')
    driver.get(config.get('login_url'))
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'login__form_action_container')))

    user_name = driver.find_element_by_xpath('//*[@id="username"]')
    password = driver.find_element_by_xpath('//*[@id="password"]')

    # send input data
    user_name.send_keys(config.get('username'))
    time.sleep(1)
    password.send_keys(config.get('password'))
    time.sleep(1)

    sign_in = driver.find_element_by_xpath('//*[@data-litms-control-urn="login-submit"]')
    sign_in.click()

    WebDriverWait(driver, 90).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'core-rail')))
    print('login success')

    search_link = 'https://www.linkedin.com/search/results/people/?facetCurrentCompany=%5B%22125241%22%5D'
    driver.get(search_link)

    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="ember54"]/div/ul')))

    base_url = 'https://www.linkedin.com/search/results/people/?facetCurrentCompany=%5B%22125241%22%5D&page={}'

    final_result = []

    for page in range(1, 100):
        page_results = get_page_result(base_url.format(page), driver)
        if not page_results:
            break
        final_result.extend(page_results)

    print('result count : {}'.format(len(final_result)))

    df = pd.DataFrame(final_result)
    return df


def main_scrape():
    print('in main scraper')
    init_config()
    status_flag = False
    try:
        for counter in range(0, config['retry_count']):
            print('Trial: {}'.format(counter + 1))
            try:
                driver = init_webdriver()
                df = linkedIn_scrape(driver)
                save_to_excel(df)
                status_flag = True
                break
            except Exception as ex:
                print('Exception block')
                print(ex)

                print(traceback.format_exc())
            finally:
                driver.close()
            time.sleep(10)
        print('end of script')
    finally:
        print('cleanup any resources')
        print('error profiles :{}'.format(len(rejected_profiles)))
        print('rejected profiles: {}'.format(rejected_profiles))

    return status_flag


if __name__ == '__main__':
    success = main_scrape()
