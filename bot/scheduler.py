import logging

logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

import time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore
from shared.db import client

jobstores = {
    "default": MongoDBJobStore("giveaways-bot", client=client)
}
# jobstores = {
#     "default": MemoryJobStore()
# }

# class SchedulerWrapper:
#     _instance = None

#     def __new__(cls):
#         if cls._instance is None:
#             cls._instance = super().__new__(cls)
#             cls._instance.scheduler = AsyncIOScheduler(jobstores=jobstores)
#             cls._instance.scheduler.start()
#             print("Scheduler started")
#         return cls._instance

#     def add_job(self, *args, **kwargs):
#         return self.scheduler.add_job(*args, **kwargs)

#     def shutdown(self):
#         self.scheduler.shutdown()


class SchedulerWrapper:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.scheduler = AsyncIOScheduler(
                jobstores=jobstores,
                serializer="json",
                coalesce=True
            )
            cls._instance.scheduler.start()
            print("Scheduler started")
        return cls._instance

    def add_job(self, *args, **kwargs):
        return self.scheduler.add_job(*args, **kwargs)

    def shutdown(self):
        self.scheduler.shutdown()
    
    def get_jobs(self):
        return self.scheduler.get_jobs()
