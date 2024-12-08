import logging
import json
import time
import random
import requests
import schedule
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
import urllib3
import datetime
from apscheduler.schedulers.background import BackgroundScheduler
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('checkin.log', encoding='utf-8')
    ]
)

task_logger = logging.getLogger('task_logger')
task_logger.setLevel(logging.INFO)
task_handler = logging.FileHandler('task.log', encoding='utf-8')
task_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
task_logger.addHandler(task_handler)

class OnefootballClient:
    def __init__(self, proxy=None):
        self.base_url = "https://api.deform.cc/"
        self.campaign_id = "5865ac91-e072-4573-8a7e-9f9e197174f2"
        self.checkin_activity_id = "73991364-c94a-4f43-a124-105827da133c"
        
        self.tasks = {
            "Share our news": "aebe9888-2657-4963-8057-c15a43dd933e",
            "Celebrate the nft": "deef2563-4865-4905-9cf0-dc12ff5cf43c",
            "like our ofc": "2555577d-7880-4420-bd78-ea24c2189892",
            "Retweet our ofc": "01a91e9e-83b2-4f9c-82fd-eafbc2065dd2",
            "Follow us": "137ea441-e56f-42b2-9f99-824ee7b892a2"
        }
        
        self.proxy = proxy
        self.session = self._create_session()

    def _create_session(self):
        session = requests.Session()
        if self.proxy:
            try:
                proxy_parts = self.proxy.split('://')
                if len(proxy_parts) == 2:
                    protocol, address = proxy_parts
                    session.proxies = {
                        'http': f'socks5h://{address}',
                        'https': f'socks5h://{address}'
                    }
                else:
                    session.proxies = {
                        'http': f'socks5h://{self.proxy}',
                        'https': f'socks5h://{self.proxy}'
                    }
            except Exception as e:
                logging.error(f"代理设置错误: {str(e)}")
                return None
        
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=1,
            pool_maxsize=1,
            max_retries=3,
            pool_block=False
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        
        session.verify = False
        session.timeout = (10, 30)
        return session

    def set_headers(self, auth_token):
        if not self.session:
            self.session = self._create_session()
        
        self.headers = {
            "authority": "api.deform.cc",
            "accept": "*/*",
            "accept-language": "zh-CN,zh;q=0.9",
            "authorization": f"Bearer {auth_token}",
            "content-type": "application/json",
            "origin": "https://deform.cc",
            "referer": "https://deform.cc/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Connection": "close" 
        }
        self.session.headers.update(self.headers)

    def make_request(self, payload, operation_name, max_retries=3):
        if not self.session:
            self.session = self._create_session()
            if not self.session:
                raise Exception("无法创建会话")

        for attempt in range(max_retries):
            try:
                response = self.session.post(
                    self.base_url,
                    json=payload,
                    timeout=(10, 30)
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise
                logging.error(f"Attempt {attempt + 1} failed: {str(e)}")
                time.sleep(2 ** attempt)
                
                
                self.session.close()
                self.session = self._create_session()
                if not self.session:
                    raise Exception("无法重新创建会话")
                self.session.headers.update(self.headers)
                continue

    def verify_activity(self, activity_id, task_name=None):
        payload = {
            "operationName": "VerifyActivity",
            "query": """mutation VerifyActivity($data: VerifyActivityInput!) {
  verifyActivity(data: $data) {
    record {
      id
      activityId
      status
      properties
      createdAt
      rewardRecords {
        id
        status
        appliedRewardType
        appliedRewardQuantity
        appliedRewardMetadata
        error
        rewardId
        reward {
          id
          quantity
          type
          properties
          __typename
        }
        __typename
      }
      __typename
    }
    missionRecord {
      id
      missionId
      status
      createdAt
      rewardRecords {
        id
        status
        appliedRewardType
        appliedRewardQuantity
        appliedRewardMetadata
        error
        rewardId
        reward {
          id
          quantity
          type
          properties
          __typename
        }
        __typename
      }
      __typename
    }
    __typename
  }
}""",
            "variables": {
                "data": {
                    "activityId": activity_id
                }
            }
        }
        
        result = self.make_request(payload, "VerifyActivity")
        
        if result and 'errors' in result:
            error = result['errors'][0]
            error_msg = error.get('extensions', {}).get('clientFacingMessage', error.get('message', '未知错误'))
            
            if "User has already completed the activity" in error_msg:
                logging.info(f"✓ {task_name}: 已完成")
                return True
            else:
                logging.error(f"✗ {task_name}: {error_msg}")
                return False
        
        if result and 'data' in result and 'verifyActivity' in result['data']:
            verify_result = result['data']['verifyActivity']
            record = verify_result.get('record', {})
            
            if record and record.get('status') == 'COMPLETED':
                reward_info = ""
                if record.get('rewardRecords'):
                    for reward in record['rewardRecords']:
                        if reward.get('status') == 'COMPLETED':
                            reward_info = f" (+{reward.get('appliedRewardQuantity', 0)} {reward.get('appliedRewardType', '')})"
                            break
                
                logging.info(f"✓ {task_name}: 完成{reward_info}")
                return True
            else:
                logging.error(f"✗ {task_name}: 验证失败")
                return False
        else:
            logging.error(f"✗ {task_name}: 响应无效")
            return False

def load_proxies(proxy_file):
    try:
        with open(proxy_file, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        logging.error(f"Failed to load proxy file: {str(e)}")
        return []

def load_accounts(account_file):
    try:
        with open(account_file, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        logging.error(f"Failed to load account file: {str(e)}")
        return []

def process_checkin(auth_token, proxy=None):
    client = OnefootballClient(proxy)
    client.set_headers(auth_token)
    
    
    time.sleep(random.uniform(1, 3))
    try:
        if client.verify_activity(client.checkin_activity_id, "每日签到"):
            return 1
    except Exception as e:
        logging.error(f"签到失败: {str(e)}")
    return 0

def process_all_tasks(auth_token, proxy=None):
    client = OnefootballClient(proxy)
    client.set_headers(auth_token)
    
    
    time.sleep(random.uniform(1, 3))
    
    tasks_completed = 0
    for task_name, activity_id in client.tasks.items():
        try:
            if client.verify_activity(activity_id, task_name):
                tasks_completed += 1
            
            time.sleep(random.uniform(0.5, 1.5))
        except Exception as e:
            logging.error(f"处理任务 {task_name} 时出错: {str(e)}")
            continue
    return tasks_completed

def process_accounts_checkin(auth_tokens, proxies):
    total_completed = 0
    max_workers = min(5, len(auth_tokens))
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i, auth_token in enumerate(auth_tokens):
            proxy = proxies[i % len(proxies)] if proxies else None
            futures.append(executor.submit(process_checkin, auth_token, proxy))
        
        for future in as_completed(futures):
            try:
                total_completed += future.result()
            except Exception as e:
                logging.error(f"处理账户签到时出错: {str(e)}")
    
    print(f"\n本次签到完成数: {total_completed}")

def process_accounts_tasks(auth_tokens, proxies):
    total_completed = 0
    max_workers = min(5, len(auth_tokens))
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i, auth_token in enumerate(auth_tokens):
            proxy = proxies[i % len(proxies)] if proxies else None
            futures.append(executor.submit(process_all_tasks, auth_token, proxy))
        
        for future in as_completed(futures):
            try:
                total_completed += future.result()
            except Exception as e:
                logging.error(f"处理账户任务时出错: {str(e)}")
    
    print(f"\n本次任务完成数: {total_completed}")

def main():
    try:
        with open('accounts.txt', 'r') as f:
            auth_tokens = [line.strip() for line in f if line.strip()]
        
        proxies = load_proxies('proxy.txt')
        if not proxies:
            logging.warning("未找到代理配置，将使用直连")
        
        while True:
            print("\n=== Onefootball 自动任务系统 ===")
            print("1. 完成所有任务")
            print("2. 启动定时签到（每12小时）")
            print("3. 退出")
            
            choice = input("请选择操作 (1-3): ").strip()
            
            if choice == '1':
                process_accounts_tasks(auth_tokens, proxies)
                
            elif choice == '2':
                scheduler = BackgroundScheduler()
                scheduler.add_job(
                    lambda: process_accounts_checkin(auth_tokens, proxies),
                    'interval',
                    hours=12,
                    next_run_time=datetime.datetime.now()
                )
                scheduler.start()
                print("定时签到任务已启动，每12小时执行一次")
                print("按 Ctrl+C 停止")
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    scheduler.shutdown()
                    print("\n定时任务已停止")
            
            elif choice == '3':
                print("退出程序")
                break
            
            else:
                print("无效选择，请重试")
                
    except Exception as e:
        logging.error(f"程序运行出错: {str(e)}")
        raise

if __name__ == '__main__':
    main()
