import os


def check_brew():
    if os.system("which brew") != 0:
        cmd = '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
        os.system(cmd)


def brew_install(dep):
    os.system("brew install {}".format(dep))


def main():
    check_brew()
    with open("./dep.txt", "r") as dep_file:
        deps = dep_file.readlines()
        for dep in deps:
            os.system("echo 'installing {}...'".format(dep))
            brew_install(dep)


if __name__ == "__main__":
    main()
