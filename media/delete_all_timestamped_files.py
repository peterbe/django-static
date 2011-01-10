import os
import re
def delete_here(dir):
    for f in os.listdir(dir):
        if os.path.isdir(os.path.join(dir, f)):
            delete_here(os.path.join(dir, f))
        elif re.findall('\.\d{10}\.', f):
            print os.path.join(dir, f)
            os.remove(os.path.join(dir, f))
if __name__ == '__main__':
    delete_here(os.path.abspath(os.path.dirname(__file__)))
    