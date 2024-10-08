import requests
import json
import time
import os
import random
from colorama import Fore, Style, init
from datetime import datetime
import signal
import sys
import re
from fake_useragent import UserAgent
from faker import Faker
from urllib.parse import parse_qs

# Initialize Colorama
init(autoreset=True)

ERROR_LOG_FILE = "error_log.txt"
FAKE_DATA_FILE = "fake_data.json"

def log_error(message, account_no=None, username=None):
    error_message = f"{datetime.now()} - "
    if account_no is not None:
        error_message += f"Account No. {account_no} - "
    if username is not None:
        error_message += f"Username: {username} - "
    error_message += message + "\n"
    
    with open(ERROR_LOG_FILE, "a") as file:
        file.write(error_message)

def save_fake_data(fake_data):
    with open(FAKE_DATA_FILE, 'w') as file:
        json.dump(fake_data, file)

def load_fake_data():
    try:
        with open(FAKE_DATA_FILE, 'r') as file:
            data = json.load(file)
            if isinstance(data, list):  # Ensure that the data is a list
                return data
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def parse_username_from_query(query):
    try:
        parsed_query = parse_qs(query)
        user_info = parsed_query.get('user', [None])[0]
        if user_info:
            user_info = json.loads(user_info)
            return user_info.get('username', 'Unknown')
    except Exception as e:
        log_error(f"Error parsing username from query: {e}")
    return 'Unknown'

def generate_fake_data(query_ids):
    fake = Faker()
    ua = UserAgent()
    fake_data = []
    common_email_domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"]

    for query in query_ids:
        username = parse_username_from_query(query)  # Extract username from query ID
        if username:
            email_domain = random.choice(common_email_domains)
            email = f"{username.replace(' ', '.').lower()}@{email_domain}"  # Create email from username

            account_data = {
                "user_agent": ua.random,
                "name": username,
                "address": fake.address(),
                "email": email
            }
            fake_data.append(account_data)

    save_fake_data(fake_data)
    return fake_data

def get_fake_data(query_ids):
    fake_data = load_fake_data()
    if fake_data is None or len(fake_data) != len(query_ids):  # Ensure the length matches query_ids
        fake_data = generate_fake_data(query_ids)
    else:
        update_needed = input("Need to update fake data information? (y/n): ").strip().lower() == 'y'
        if update_needed:
            fake_data = generate_fake_data(query_ids)
            save_fake_data(fake_data)
    return fake_data

def get_headers(token, user_agent):
    return {
        "accept": "application/json, text/plain, */*",
        "authorization": f"Bearer {token}",
        "User-Agent": user_agent
    }

def extract_browser_info(user_agent):
    browser_match = re.search(r"(Firefox|Chrome|Safari|Opera|Edge|MSIE|Trident)", user_agent)
    os_match = re.search(r"\(([^;]+)", user_agent)  # Simplified OS extraction
    
    browser_info = browser_match.group(1) if browser_match else "Unknown Browser"
    os_info = os_match.group(1) if os_match else "Unknown OS"
    
    return browser_info, os_info

def get_new_token(query_id, user_agent=None):
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/json",
        "origin": "https://telegram.blum.codes",
        "referer": "https://telegram.blum.codes/",
        "User-Agent": user_agent
    }
    data = json.dumps({"query": query_id})
    url = "https://user-domain.blum.codes/api/v1/auth/provider/PROVIDER_TELEGRAM_MINI_APP"
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()
            response_json = response.json()
            token = response_json.get('token', {}).get('refresh', None)
            if token:
                return token
        except requests.RequestException as e:
            log_error(f"Error generating token on attempt {attempt+1}: {e}")
            time.sleep(random.uniform(1, 2))  # Retry delay
    return None

def get_task(token, user_agent=None):
    url = "https://earn-domain.blum.codes/api/v1/tasks"
    try:
        response = requests.get(url=url, headers=get_headers(token=token, user_agent=user_agent), timeout=20)
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        log_error(f"Error fetching tasks: {e}")
        return []

def claim_farming(token, user_agent=None):
    url = "https://game-domain.blum.codes/api/v1/farming/claim"
    headers = get_headers(token, user_agent)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers)
            if response.status_code == 200:
                print(f"{Fore.GREEN + Style.BRIGHT}Farming Claimed Successfully [✓]{Style.RESET_ALL}")
                return True
            elif response.status_code == 425:
                print(f"{Fore.RED + Style.BRIGHT}Farming Already Claimed [✓]{Style.RESET_ALL}")
                return False
        except requests.RequestException:
            time.sleep(2)  # Retry delay without showing logs
    return False

def check_farming_status(token, user_agent=None):
    url = "https://game-domain.blum.codes/api/v1/user/balance"
    headers = get_headers(token, user_agent)
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        timestamp = data.get("timestamp", 0) / 1000
        end_farming = data.get("farming", {}).get("endTime", 0) / 1000
        return timestamp > end_farming or end_farming == 0
    except requests.RequestException as e:
        log_error(f"Error checking farming status: {e}")
    return False

def start_farming(token, user_agent=None):
    if check_farming_status(token, user_agent=user_agent):
        url_farming = "https://game-domain.blum.codes/api/v1/farming/start"
        headers = get_headers(token, user_agent)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(url_farming, headers=headers)
                response.raise_for_status()
                data = response.json()
                end_time = data.get("endTime", None)
                if end_time:
                    end_date = datetime.fromtimestamp(end_time / 1000)
                    print(f"{Fore.GREEN + Style.BRIGHT}Farming Successfully Started [✓]{Style.RESET_ALL}")
                    print(f"{Fore.GREEN + Style.BRIGHT}End Farming: {end_date}{Style.RESET_ALL}")
                    return end_date
            except requests.RequestException as e:
                log_error(f"Error starting farming on attempt {attempt+1}: {e}")
                time.sleep(random.uniform(1, 2))  # Retry delay
    else:
        print(f"{Fore.RED + Style.BRIGHT}Farming Already Started [✓]{Style.RESET_ALL}")
    return None

def get_daily_reward(token, user_agent=None):
    url = "https://game-domain.blum.codes/api/v1/daily-reward"
    headers = get_headers(token, user_agent)
    max_retries = 3  # Set the number of retries

    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers)
            response.raise_for_status()
            print(f"{Fore.GREEN + Style.BRIGHT}Daily Reward Claimed Successfully [✓]{Style.RESET_ALL}")
            return True
        except requests.HTTPError as e:
            if response.status_code == 400:
                print(f"{Fore.RED + Style.BRIGHT}Daily Reward already claimed [✓]{Style.RESET_ALL}")
                return False
            log_error(f"Attempt {attempt+1}: Error claiming daily reward: {e}")
            time.sleep(random.uniform(1, 2))  # Retry delay

    print(f"{Fore.RED + Style.BRIGHT}Failed to claim Daily Reward after {max_retries} attempts.{Style.RESET_ALL}")
    return False

def process_all_tasks(token, exclude_task_names, user_agent=None):
    try:
        earn_section = get_task(token=token, user_agent=user_agent)
        if not earn_section:
            print(f"{Fore.RED + Style.BRIGHT}No tasks fetched. Exiting task processing.{Style.RESET_ALL}")
            return

        processed_ids = set()
        for earn in earn_section:
            tasks = earn.get("tasks", []) + earn.get("subSections", [])
            for task in tasks:
                if isinstance(task, dict):
                    sub_tasks = task.get("tasks", task.get("subTasks", []))
                    for sub_task in sub_tasks:
                        task_id = sub_task["id"]
                        task_name = sub_task["title"]
                        if task_name not in exclude_task_names and task_id not in processed_ids:
                            task_status = sub_task["status"]
                            process_task(token, task_id, task_name, task_status, {}, user_agent, False)
                            processed_ids.add(task_id)
    except Exception as e:
        log_error(f"Error processing all tasks: {e}")

def get_task_keywords(task_name_file, keyword_file):
    task_keywords = {}
    try:
        with open(task_name_file, "r") as names_file, open(keyword_file, "r") as keywords_file:
            task_names = names_file.readlines()
            keywords = keywords_file.readlines()
            for i, task_name in enumerate(task_names):
                task_name = task_name.strip()
                if i < len(keywords):
                    keyword = keywords[i].strip()
                    task_keywords[task_name] = keyword
    except FileNotFoundError as e:
        log_error(f"File not found: {e}")
    return task_keywords

def process_task(token, task_id, task_name, task_status, task_keywords, user_agent=None, is_validation_required=False):
    if task_status == "FINISHED":
        print(f"{Fore.RED + Style.BRIGHT}{task_name}: Already completed!{Style.RESET_ALL}")
        return
    elif task_status == "NOT_STARTED":
        start_task(token, task_id, user_agent)
        task_status = "READY_FOR_VERIFY"  # Silently start the task if not started
    if task_status == "READY_FOR_CLAIM":
        claim_status = claim_task(token=token, task_id=task_id, user_agent=user_agent)
        if claim_status == "FINISHED":
            print(f"{Fore.GREEN + Style.BRIGHT}{task_name}: Successfully claimed!{Style.RESET_ALL}")
    elif task_status == "READY_FOR_VERIFY":
        keyword = task_keywords.get(task_name)
        if is_validation_required and keyword:
            if validate_task(token, task_id, keyword, user_agent):
                print(f"{Fore.GREEN + Style.BRIGHT}{task_name}: Successfully claimed!{Style.RESET_ALL}")

def start_task(token, task_id, user_agent=None):
    url = f"https://earn-domain.blum.codes/api/v1/tasks/{task_id}/start"
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(url=url, headers=get_headers(token=token, user_agent=user_agent), json={}, timeout=20)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            log_error(f"Error starting task {task_id} on attempt {attempt+1}: {e}")
            time.sleep(random.uniform(1, 2))  # Retry delay
    return None

def claim_task(token, task_id, user_agent=None):
    url = f"https://earn-domain.blum.codes/api/v1/tasks/{task_id}/claim"
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(url=url, headers=get_headers(token=token, user_agent=user_agent), json={}, timeout=20)
            response.raise_for_status()
            return response.json().get("status")
        except requests.HTTPError:
            time.sleep(random.uniform(1, 2))  # Retry delay
    return None

def validate_task(token, task_id, keyword, user_agent=None):
    url = f"https://earn-domain.blum.codes/api/v1/tasks/{task_id}/validate"
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(url=url, headers=get_headers(token=token, user_agent=user_agent), json={"keyword": keyword}, timeout=20)
            response.raise_for_status()
            if response.json().get("status") == "READY_FOR_CLAIM":
                claim_status = claim_task(token=token, task_id=task_id, user_agent=user_agent)
                if claim_status == "FINISHED":
                    return True
        except requests.HTTPError as e:
            log_error(f"Error validating task {task_id} on attempt {attempt+1}: {e}")
            time.sleep(random.uniform(1, 2))  # Retry delay
    return False

def new_balance(token, user_agent=None):
    url = "https://game-domain.blum.codes/api/v1/user/balance"
    headers = get_headers(token, user_agent)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data_balance = response.json()
            new_balance = data_balance.get("availableBalance", "N/A")
            play_passes = data_balance.get("playPasses", 0)
            return new_balance, play_passes
        except requests.RequestException as e:
            log_error(f"Error retrieving new balance on attempt {attempt+1}: {e}")
            time.sleep(random.uniform(1, 2))  # Retry delay
    return None, None

def clear_token_file(file_path):
    try:
        with open(file_path, 'w') as file:
            file.write('')
        print(f"{Fore.GREEN + Style.BRIGHT}Token file cleared successfully.{Style.RESET_ALL}")
    except Exception as e:
        log_error(f"Error clearing token file: {e}")

def save_token(token, file_path):
    try:
        with open(file_path, 'w') as file:
            file.write(token)
    except Exception as e:
        log_error(f"Error saving token: {e}")

def countdown_timer(seconds):
    for remaining in range(seconds, 0, -1):
        mins, secs = divmod(remaining, 60)
        hours, mins = divmod(mins, 60)
        print(f"{Fore.CYAN + Style.BRIGHT}Wait {hours:02}:{mins:02}:{secs:02}{Style.RESET_ALL}", end='\r')
        time.sleep(1)
    print(' ' * 40, end='\r')

def check_daily_reward_time():
    current_time = datetime.now()
    target_time = current_time.replace(hour=11, minute=0, second=0, microsecond=0)
    return current_time >= target_time

def play_game(token, user_agent=None):
    url = "https://game-domain.blum.codes/api/v1/game/play"
    headers = get_headers(token, user_agent)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            game_id = data.get("gameId")
            if game_id:
                return game_id
        except requests.RequestException as e:
            log_error(f"Error starting game on attempt {attempt+1}: {e}")
            time.sleep(random.uniform(1, 2))  # Retry delay
    return None

def claim_game(token, game_id, points, user_agent=None):
    url = "https://game-domain.blum.codes/api/v1/game/claim"
    headers = get_headers(token, user_agent)
    body = {"gameId": game_id, "points": points}
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=body)
            response.raise_for_status()
            return points  # Return points claimed without printing here
        except requests.RequestException as e:
            log_error(f"Error claiming game reward on attempt {attempt+1}: {e}")
            time.sleep(random.uniform(1, 2))  # Retry delay
    return 0

def auto_play_game(token, user_agent=None, game_points_min=121, game_points_max=210):
    total_reward = 0
    play_time = 32  # Play for 32 seconds

    while True:
        current_balance, play_passes = new_balance(token, user_agent=user_agent)
        if current_balance is None or play_passes is None:
            log_error("Failed to retrieve balance or play passes.")
            break

        if play_passes == 0:
            print(f"{Fore.RED + Style.BRIGHT}°Pass : 0, moving to next process.{Style.RESET_ALL}")
            print(f"{Fore.GREEN + Style.BRIGHT}Total Reward: {total_reward}{Style.RESET_ALL}")
            break  # Skip to next process if no play passes

        print(f"{Fore.YELLOW + Style.BRIGHT}Playing Game.....°Pass: {play_passes}{Style.RESET_ALL}")
        
        game_id = play_game(token, user_agent=user_agent)
        if game_id:
            # Live timer display during game play
            for remaining in range(play_time, 0, -1):
                mins, secs = divmod(remaining, 60)
                print(f"{Fore.YELLOW + Style.BRIGHT}{mins:02}:{secs:02}{Style.RESET_ALL}", end='\r')
                time.sleep(1)
            print()  # Move to the next line after timer

            points = random.randint(game_points_min, game_points_max)
            reward = claim_game(token, game_id, points, user_agent=user_agent)
            total_reward += reward
            
            # Show claimed points after game ends
            print(f"{Fore.GREEN + Style.BRIGHT}Successfully claimed {points} points [✓]{Style.RESET_ALL}")

            # Wait 3 to 7 seconds before starting a new game play
            wait_time = random.randint(3, 7)
            for remaining in range(wait_time, 0, -1):
                print(f"{Fore.CYAN + Style.BRIGHT}Waiting...⌛ {remaining} seconds{Style.RESET_ALL}", end='\r')
                time.sleep(1)
            print(' ' * 40, end='\r')

def art():
    print(Fore.GREEN + Style.BRIGHT + r"""
  _                
 | | | |             | |               
 | |_| |  __ _   ___ | | __  ___  _ __ 
 |  _  | / _` | / __|| |/ / / _ \| '__|
 | | | || (_| || (__ |   < |  __/| |   
 \_| |_/ \__,_| \___||_|\_\ \___||_| 
    """ + Style.RESET_ALL)

    print(Fore.CYAN + Style.BRIGHT + "Blum Script Edited by @Dhiraj_9619 💫 DHEERAJ" + Style.RESET_ALL)

def main():
    signal.signal(signal.SIGINT, signal_handler)  # Handle Ctrl+C to exit gracefully
    clear_terminal()
    art()

    query_ids = get_query_ids_from_file('data.txt')
    fake_data = get_fake_data(query_ids)

    task_ids_for_earn_checking_social = [
        "33ddee08-2ef4-45ef-b243-8d80c6b32009",
        "3f1502b8-9e87-4b3a-995d-81c135f29f27",
        "1e5faaca-6d17-4f3b-96aa-537a112c1e68",
        "97d50b4c-a070-4136-a41d-390e67b883e0",
        "7ec46833-c5bf-4320-827e-fb04ab740972",     
        "4098fa89-3b83-42d6-a987-a9b8a6f40caf"
    ]

    exclude_task_names_option1 = {
        "Invite",
        "Farm",
        "Launch Tongotchi mini-app",
        "Join Tongotchi on TG",
        "Join or create tribe",
        "Connect TON wallet"
    }

    new_task_names = set()
    with open('New_task_name.txt', 'r') as new_task_file:
        new_task_names = {line.strip() for line in new_task_file}

    # Default game points
    game_points_min = 121
    game_points_max = 210

    while True:
        total_balance = 0.0
        print("\n" + Fore.MAGENTA + Style.BRIGHT + "="*50 + Style.RESET_ALL)
        print(f"{Fore.YELLOW + Style.BRIGHT}Choose an option:{Style.RESET_ALL}")
        print(Fore.MAGENTA + Style.BRIGHT + "="*50 + Style.RESET_ALL)
        print(f"{Fore.CYAN + Style.BRIGHT}1. All Tasks{Style.RESET_ALL}")
        print(f"{Fore.CYAN + Style.BRIGHT}2. Auto Farming{Style.RESET_ALL}")
        print(f"{Fore.CYAN + Style.BRIGHT}3. Auto Play Game{Style.RESET_ALL}")
        print(f"{Fore.CYAN + Style.BRIGHT}4. Earn for Checking Social Tasks{Style.RESET_ALL}")
        print(f"{Fore.CYAN + Style.BRIGHT}5. New Task (Keywords Task Only){Style.RESET_ALL}")
        print(f"{Fore.CYAN + Style.BRIGHT}6. Game Point Settings{Style.RESET_ALL}")
        print(f"{Fore.CYAN + Style.BRIGHT}7. Exit Program{Style.RESET_ALL}")
        print(Fore.MAGENTA + Style.BRIGHT + "="*50 + Style.RESET_ALL)
        user_choice = input("Enter your choice (1, 2, 3, 4, 5, 6, 7): ").strip()

        if user_choice not in ['1', '2', '3', '4', '5', '6', '7']:
            continue

        if user_choice == '7':
            exit_program()  # Exit the program gracefully

        if user_choice == '6':
            # Game Point Settings
            try:
                game_points_min = int(input("Enter minimum game points (default 121): ").strip())
                game_points_max = int(input("Enter maximum game points (default 210, max 280): ").strip())
                
                if game_points_max > 280:
                    print(f"{Fore.RED + Style.BRIGHT}Maximum game points cannot exceed 280! Setting to 280.{Style.RESET_ALL}")
                    game_points_max = 280

                if game_points_min < 0 or game_points_max < game_points_min:
                    print(f"{Fore.RED + Style.BRIGHT}Invalid input for game points. Reverting to defaults.{Style.RESET_ALL}")
                    game_points_min = 121
                    game_points_max = 210

            except ValueError:
                print(f"{Fore.RED + Style.BRIGHT}Invalid input! Reverting to default point settings.{Style.RESET_ALL}")
                game_points_min = 121
                game_points_max = 210

            continue

        start_account = input("Enter the Account no to start the process from: ").strip()
        try:
            start_account = int(start_account) - 1
        except ValueError:
            start_account = 0

        for index in range(start_account, len(query_ids)):
            query_id = query_ids[index]

            if not query_id:
                log_error("Query ID not found.", index + 1)
                continue

            username = parse_username_from_query(query_id)

            print(f"{Fore.CYAN + Style.BRIGHT}--- Account No. {index + 1} ---{Style.RESET_ALL}")
            print(f"{Fore.CYAN + Style.BRIGHT}Username: {username}{Style.RESET_ALL}")

            user_agent = fake_data[index]['user_agent']

            # Extract and display browser and OS info
            browser_info, os_info = extract_browser_info(user_agent)
            print(f"{Fore.MAGENTA + Style.BRIGHT}{browser_info}, {os_info}{Style.RESET_ALL}")

            token = None
            for attempt in range(3):
                token = get_new_token(query_id, user_agent=user_agent)
                if token:
                    break
                log_error(f"Token generation failed on attempt {attempt+1}", index + 1, username)
                time.sleep(random.uniform(1, 2))  # Retry delay

            if not token:
                continue

            save_token(token, 'token.txt')

            prev_balance, _ = new_balance(token, user_agent=user_agent)
            print(f"{Fore.GREEN + Style.BRIGHT}Previous Balance: {prev_balance}{Style.RESET_ALL}")

            try:
                # Perform daily check-in at the beginning of all options
                if not check_daily_reward_time():
                    print(f"{Fore.YELLOW + Style.BRIGHT}Daily check-in will work after 11:00 AM.{Style.RESET_ALL}")
                else:
                    if get_daily_reward(token, user_agent=user_agent):
                        countdown_timer(random.randint(2, 3))

                if user_choice == '1':
                    if claim_farming(token, user_agent=user_agent):
                        countdown_timer(random.randint(2, 3))
                    start_farming(token, user_agent=user_agent)

                    # Exclude tasks from new_task_names and predefined exclude_task_names
                    exclude_set = exclude_task_names_option1.union(new_task_names)
                    process_all_tasks(token, exclude_task_names=exclude_set, user_agent=user_agent)

                if user_choice == '2':
                    if claim_farming(token, user_agent=user_agent):
                        countdown_timer(random.randint(2, 3))
                    start_farming(token, user_agent=user_agent)

                if user_choice == '3':  # Auto Play Game Logic
                    auto_play_game(token, user_agent=user_agent, game_points_min=game_points_min, game_points_max=game_points_max)

                if user_choice == '4':  # Earn for Checking Social Tasks
                    process_tasks_by_id(token, task_ids_for_earn_checking_social, user_agent=user_agent)

                if user_choice == '5':  # New Task
                    # Only process tasks that are in the New_task_name.txt
                    process_new_tasks_only(token, user_agent, new_task_names)

            except Exception as e:
                log_error(f"Error during processing: {e}", index + 1, username)

            finally:
                updated_balance, _ = new_balance(token, user_agent=user_agent)
                print(f"{Fore.GREEN + Style.BRIGHT}Final Balance: {updated_balance}{Style.RESET_ALL}")

                if updated_balance is not None:
                    total_balance += float(updated_balance or 0)

                # Wait for 2-3 seconds before processing the next account
                countdown_timer(random.randint(2, 3))

                # Add a blank line after processing each account
                print()

        print(f"{Fore.YELLOW + Style.BRIGHT}Total Balance of all accounts: {total_balance}{Style.RESET_ALL}")

        clear_token_file('token.txt')

def process_tasks_by_id(token, task_ids, user_agent=None):
    try:
        earn_section = get_task(token=token, user_agent=user_agent)
        if not earn_section:
            print(f"{Fore.RED + Style.BRIGHT}No tasks fetched. Exiting task processing.{Style.RESET_ALL}")
            return

        processed_ids = set()
        for earn in earn_section:
            tasks = earn.get("tasks", []) + earn.get("subSections", [])
            for task in tasks:
                if isinstance(task, dict):
                    sub_tasks = task.get("tasks", task.get("subTasks", []))
                    for sub_task in sub_tasks:
                        task_id = sub_task["id"]
                        if task_id in task_ids and task_id not in processed_ids:
                            task_status = sub_task["status"]
                            if start_and_claim_task(token, task_id, task_status, user_agent):
                                random_delay = random.randint(3, 5)
                                countdown_timer(random_delay)
                            processed_ids.add(task_id)
    except Exception as e:
        log_error(f"Error processing tasks by ID: {e}")

def start_and_claim_task(token, task_id, task_status, user_agent=None):
    if task_status == "FINISHED":
        print(f"{Fore.RED + Style.BRIGHT}Task ID {task_id}: Already completed!{Style.RESET_ALL}")
        return False
    elif task_status == "NOT_STARTED":
        start_task(token, task_id, user_agent)
        task_status = "READY_FOR_CLAIM"  # Skip validation and move to claim
    if task_status == "READY_FOR_CLAIM":
        claim_status = claim_task(token=token, task_id=task_id, user_agent=user_agent)
        if claim_status == "FINISHED":
            print(f"{Fore.GREEN + Style.BRIGHT}Task ID {task_id}: Successfully claimed!{Style.RESET_ALL}")
            return True
    return False

def process_new_tasks_only(token, user_agent=None, new_task_names=set()):
    try:
        earn_section = get_task(token=token, user_agent=user_agent)
        if not earn_section:
            print(f"{Fore.RED + Style.BRIGHT}No tasks fetched. Exiting task processing.{Style.RESET_ALL}")
            return

        processed_ids = set()  # Set to track processed task IDs
        task_keywords = get_task_keywords('New_task_name.txt', 'Keyword.txt')

        for earn in earn_section:
            tasks = earn.get("tasks", []) + earn.get("subSections", [])
            for task in tasks:
                if isinstance(task, dict):
                    sub_tasks = task.get("tasks", task.get("subTasks", []))
                    for sub_task in sub_tasks:
                        task_id = sub_task["id"]
                        task_name = sub_task["title"]
                        task_status = sub_task["status"]

                        if task_id in processed_ids:
                            continue  # Skip already processed tasks

                        if task_name in new_task_names:
                            processed_ids.add(task_id)  # Mark the task as processed
                            process_task(token, task_id, task_name, task_status, task_keywords, user_agent, is_validation_required=True)

    except Exception as e:
        log_error(f"Error processing new tasks: {e}")

def get_query_ids_from_file(file_path):
    try:
        with open(file_path, 'r') as file:
            query_ids = [line.strip() for line in file.readlines()]
            return query_ids
    except FileNotFoundError:
        log_error(f"File '{file_path}' not found.")
        return []
    except Exception as e:
        log_error(f"Error reading query IDs: {e}")
        return []

def exit_program():
    print("Exiting the program gracefully...")
    sys.exit(0)

def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')

def signal_handler(sig, frame):
    if sig == signal.SIGINT:  # Ctrl+C
        exit_program()

if __name__ == "__main__":
    main()
