import multiprocessing

workers = multiprocessing.cpu_count() * 2 + 1
threads = 4
timeout = 360
bind = "0.0.0.0:5269"
worker_class = "uvicorn.workers.UvicornWorker"
