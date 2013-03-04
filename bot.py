import subprocess

if __name__ == "__main__":
    with open('bot.txt', 'r') as bot_input:
        proc = subprocess.Popen(['/bin/sh'], stdin=subprocess.PIPE)
        proc.stdin.write("/opt/local/bin/python2.7 main.py\n")
        for line in bot_input:
            proc.stdin.write(line)
