import os


def post_worker_init(worker):
    open(f"/tmp/worker_{os.getpid()}", "w+").close()


def worker_exit(server, worker):
    os.remove(f"/tmp/worker_{os.getpid()}")
