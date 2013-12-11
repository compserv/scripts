from hknmod import add_dead_user
from sys import argv

def main():
    if len(argv) != 6:
        print "login committee first_name last_name"
    else:
        #print "add_dead_user", argv[1], argv[2], argv[3], argv[4], argv[5]
        add_dead_user(argv[1], argv[2], argv[3], argv[4], argv[5])

main()
