
import random

import threading
import time
from queue import Queue
from typing import Any

import undetected_chromedriver as uc

from langchain.tools import BaseTool
from pydantic import PrivateAttr
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

import atexit


class UndetectedBrowserTool(BaseTool):
    name: str = "undetected_browser_tool"
    description: str = "Fetch the text content from a webpage URL using Selenium"
    task_queue: Queue = PrivateAttr(default=None)
    driver: Any = PrivateAttr(default=None)
    worker_thread: threading.Thread = PrivateAttr(default=None)
    headless: bool = PrivateAttr()
    additional_opts: dict = PrivateAttr()
    as_text: bool = True
    
    def __init__(self, headless: bool = True, as_text: bool = True, additional_opts: dict = {}, **kwargs):
        super().__init__(**kwargs)
        self.headless = headless
        self.additional_opts = additional_opts
        self.task_queue = Queue()
        self.as_text = as_text
        atexit.register(self.cleanup)
        self.initialize_driver(additional_opts)

    def initialize_driver(self, additional_opts):
        options = uc.ChromeOptions()
        if self.headless:
            options.add_argument("--headless")

        for key, value in additional_opts.items():
            options.add_argument(f"--{key}={value}")
            
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        self.driver = uc.Chrome(options=options)
        self.driver.set_page_load_timeout(30)
        self.driver.implicitly_wait(10)

        self.worker_thread = threading.Thread(target=self.process_queue, daemon=True)
        self.worker_thread.start()
    
    def process_queue(self):
        while True:
            try:
                url, result_queue = self.task_queue.get()
                result = self.fetch_page(url)
                result_queue.put(result)
            except Exception as e:
                result_queue.put(f"Error: {str(e)}")
            finally:
                self.task_queue.task_done()
    
    def fetch_page(self, url: str) -> str:
        try:
            self.driver.get(url)
            time.sleep(random.uniform(1, 5))
            return self.driver.find_element(By.TAG_NAME, "body").text.strip()
        except Exception as e:
            raise RuntimeError(f"Failed to fetch page: {url}") from e
    
    def run(self, url: str) -> str:
        return self.fetch_page(url)
    
    def cleanup(self):
        try:
            if self.driver:
                self.driver.quit()
        except Exception as e:
            print(f"Error during cleanup: {e}")

            
            
