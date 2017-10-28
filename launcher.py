from __future__ import print_function
import os
import sys
import subprocess
import argparse
try:
    import pip
except ImportError:
    pip = None

title = ("--------------------------\n"
         "Houdini - Launcher\n"
         "--------------------------\n")
interactive = not len(sys.argv) > 1
devnull = open(os.devnull, 'w')

def parse_cli_arguments():
     parser = argparse.ArgumentParser(description="Houdini launcher")
     parser.add_argument("--start", "-s",
                         help="Starts Houdini Servers",
                         action="store_true")
     parser.add_argument("--auto-restart",
                         help="Auto-restarts Houdini Servers",
                         action="store_true")
     parser.add_argument("--update-houdini",
                         help="Updates Houdini from latest commits",
                         action="store_true")
     parser.add_argument("--update-reqs",
                         help="Updates requirements through pip",
                         action="store_true")
     return parser.parse_args()

# Functions

def update_reqs():
    interpreter = sys.executable

    if interpreter is None:
        print("Python interpreter not found.")
        return
    os.chdir(dirname)
    args = [
        interpreter, "-m",
        "pip", "install",
        "--upgrade",
        "-r", "requirements.txt"
    ]

    code = subprocess.call(args)

    if code == 0:
        print("\nRequirements installed/updated.")
    else:
        print("\nAn error occurred while using pip. Please insure that pip is installed.\n")

def update_houdini():
    try:
        code = subprocess.call(("git", "pull", "origin", "master"))
    except IOError:
        print("\nError: Git not found. Please ensure Git is installed "
              "and present in the PATH environment variable")
        return
    if code == 0:
        print("\nHoudini was succesfully updated")
    else:
        print("\nAn unexpected error occurred. Please ensure:\n"
              " - You have not made any local edits."
              " - You have an interent connection.")

def run_houdini(autorestart):
    interpreter = sys.executable

    if verify_requirements() == False:
        print("\nYou don't have the requirements to run Houdini. "
              "Install them from the launcher.\n")
        if not interactive:
            exit(1)

    cmd = (interpreter, "houdini.py")

    while True:
        try:
            code = subprocess.call(cmd)
        except KeyboardInterrupt:
            code = 0
            break
        else:
            if code == 0:
                break
            elif code == 26:
                print("Restarting Houdini...")
                continue
            else:
                if not autorestart:
                    break

    print("Houdini has been terminated. Exit code: %d" % code)

    if interactive:
        wait()

# Global functions

def update_perms(func, path, excinfo):
    os.chmod(path, 0o755)
    func(path)

def clear_screen():
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")

def wait():
    if interactive:
        raw_input("Press enter to continue.")

def user_choice():
    return raw_input("> ").lower().strip()

def verify_requirements():
    try:
        import bcrypt
        import redis
        import sqlalchemy
        import twisted
        import watchdog
        return True
    except Exception as e:
        print(e)
        return False

# Checks

def git_check():
    try:
        subprocess.call(["git", "--version"], stdout=devnull,
                                              stdin =devnull,
                                              stderr=devnull)
    except IOError:
        return False
    else:
        return True


def main():
    print("Verifying git installation...")
    has_git = git_check()
    git_cloned = os.path.isdir(".git")
    if os.name == "nt":
        os.system("TITLE Houdini - Launcher")
    clear_screen()

    while True:
        print(title)

        if not git_cloned:
            print("WARNING: Houdini was not cloned using git. "
                  "This launcher will not be able to perform core updates.\n")

        if not has_git:
            print("WARNING: Git not found. This means that it's either not "
                  "installed or not in the PATH environment variable like "
                  "requested in the guide.\n")

        print("1. Run Houdini /w autorestart in case of issues")
        print("2. Run Houdini")
        print("3. Update Houdini")
        print("4. Install/Update requirements")
        print("\n0. Quit")
        choice = user_choice()
        if choice == "1":
            run_houdini(autorestart=True)
        elif choice == "2":
            run_houdini(autorestart=False)
        elif choice == "3":
            update_houdini()
            wait()
        elif choice == "4":
            update_reqs()
            wait()
        elif choice == "0":
            break
        clear_screen()

args = parse_cli_arguments()

if __name__ == '__main__':
    abspath = os.path.abspath(__file__)
    dirname = os.path.dirname(abspath)
    os.chdir(dirname)

    if not sys.version_info >= (2, 7):
        print("Houdini requires Python 2.7 to run. "
              "Please install Python2.7 and try again. \nPress enter to continue.")
        if interactive:
            wait()
        exit(1)
    if pip is None:
        print("Houdini requires external modules which are installed through pip. "
              "Please install Pip 2.7 and try again.")
        wait()
        exit(1)
    if args.update_houdini:
        update_houdini()
    if args.update_reqs:
        update_reqs()
    if interactive:
        main()
    elif args.start:
        print("Starting Houdini...")
        run_houdini(autorestart=args.auto_restart)
