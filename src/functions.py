# coding=utf-8
from context import CONTEXT
import subprocess


def call(args, **kwargs):
    error = False
    try:
        output = subprocess.check_output(args, stderr=subprocess.STDOUT, **kwargs).decode()
    except subprocess.CalledProcessError as e:
        output = e.output.decode()
        # log crashed command
        cmd = " ".join(args) if type(args) == list else args
        
        outputlog = addOutput('[+] "' + cmd + '" crashed with output', output, True)
        CONTEXT.LOGGER.warning(outputlog)
        error = True
    
    return output, error



def addOutput(identifier, msg, err):
    if msg.strip() == '' and not err:
        return ''

    ret = identifier
    if err:
        ret = ret.replace("[+]", "[-]")
        ret += " (CRASHED):\n"
    else:
        ret += ":\n"
    ret += msg.strip()
    ret = ret.replace("\n", "\n    ")
    ret += "\n" if msg.strip() == '' else "\n\n"

    return ret