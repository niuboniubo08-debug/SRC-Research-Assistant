import subprocess

PASSWORD = 'phase3-acceptance-secret'

def execute(user_input):
    eval(user_input)
    subprocess.run('echo ' + user_input, shell=True)

def load(blob):
    import pickle
    return pickle.loads(blob)
