import sys

from core.projectOn import log_unhandled_exception, ProjectOn

if __name__ == "__main__":
    sys.excepthook = log_unhandled_exception
    ProjectOn()