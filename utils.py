import os


def prepare_dir(dir_path: str):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
