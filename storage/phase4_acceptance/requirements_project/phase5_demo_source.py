import subprocess
def run(value):
    eval(value)
    subprocess.run('echo ' + value, shell=True)
