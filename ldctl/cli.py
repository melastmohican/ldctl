import glob
import os
import re
import subprocess
import sys

import click as click

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
AGENTS_PATH = os.path.join(os.environ['HOME'], "Library/LaunchAgents")
ALL_AGENTS = [f[:-6] for f in os.listdir(AGENTS_PATH) if f.endswith('.plist')]
ALL_AGENTS_REGEX = "|".join(ALL_AGENTS)
UID = os.getuid()


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(version='1.0.0')
def main():
    pass


def get_agent(agent, agents_path=AGENTS_PATH):
    agent_search = glob.glob("{}/*{}*.plist".format(agents_path, agent))
    agents_found = len(agent_search)

    if agents_found == 0:
        print("error: no agents found for \"{}\"".format(agent), file=sys.stderr)
        sys.exit(1)
    elif agents_found == 1:
        idx = 0
    else:
        agent_exact_search = glob.glob("{}/*.{}.*plist".format(agents_path, agent))
        if len(agent_exact_search) == 1:
            agent_search = agent_exact_search
            idx = 0
        else:
            print("{} agents found for \"{}\":".format(agents_found, agent), file=sys.stderr)
            for i in range(len(agent_search)):
                agent = os.path.basename(agent_search[i])
                agent = re.sub(".plist$", "", agent)
                print(f"  [{i + 1}] {agent}")
            while True:
                try:
                    j = int(input("Select: "))
                    if 1 <= j <= agents_found:
                        idx = j - 1
                        break
                    else:
                        print("number not in range, try again", file=sys.stderr)
                except ValueError:
                    print("not a valid number, try again", file=sys.stderr)

    agent_plist = agent_search[idx]
    agent_name = os.path.basename(agent_plist)
    agent_name = re.sub(".plist$", "", agent_name)
    print(f"agent_plist={agent_plist}, agent_name={agent_name}")
    return agent_plist, agent_name


@main.command()
@click.argument('agent')
def cat(agent):
    """display content of agent file"""
    agent_plist, agent_name = get_agent(agent)
    with open(agent_plist, "r") as f:
        print(f.read(), end="")


@main.command()
@click.argument('agent')
def edit(agent):
    """edit agent file"""
    agent_plist, agent_name = get_agent(agent)
    subprocess.run([os.environ.get("EDITOR", "vim"), agent_plist])


@main.command()
@click.argument('agent')
def file(agent):
    """print agent file info"""
    agent_plist, agent_name = get_agent(agent)
    print(agent_plist)


@main.command()
def disabled(uid=UID, all_agents_regex=ALL_AGENTS_REGEX):
    """print disabled agents"""
    result = subprocess.run(["launchctl", "print-disabled", f"gui/{uid}"], stdout=subprocess.PIPE, check=True)
    result_str = result.stdout.decode("utf-8")
    lines = result_str.splitlines()
    filtered_lines = [line for line in lines if
                      "disabled" in line and any(agent in line for agent in all_agents_regex.split("|"))]
    disabled_agents = []
    for line in filtered_lines:
        disabled_agents.append(line.split('"')[1])
    print("\n".join(disabled_agents))


@main.command()
@click.argument('agent')
def less(agent):
    """less agent logs"""
    files = logfiles(agent)
    if files:
        subprocess.run([os.environ.get("PAGER", "less"), "+G"] + files)


def logfiles(agent, uid=UID):
    """agent log files"""
    agent_plist, agent_name = get_agent(agent)
    result = subprocess.run(["launchctl", "print", f"gui/{uid}/{agent_name}"], stdout=subprocess.PIPE, check=True)
    result_str = result.stdout.decode("utf-8")
    files = []
    for line in result_str.splitlines():
        if "std" in line and "path" in line:
            files.append(line.split(" = ")[1])
    return files


@main.command(name='logfiles')
@click.argument('agent')
def logfiles_command(agent):
    """print agent log files"""
    for line in logfiles(agent):
        print(line)


@main.command()
@click.argument('agent')
def tail(agent):
    """tail agent"""
    files = logfiles(agent)
    if files:
        for f in files:
            print(f"tail -50f {f}")
            subprocess.run(["tail", "-50f", f])


@main.command()
@click.argument('agent')
def blame(agent, uid=UID):
    """blame agent"""
    agent_plist, agent_name = get_agent(agent)
    subprocess.run(["launchctl", "blame", f"gui/{uid}/{agent_name}"], check=True)


@main.command()
@click.argument('agent')
def bootout(agent, uid=UID):
    """bootout agent"""
    agent_plist, agent_name = get_agent(agent)
    subprocess.run(["launchctl", "bootout", f"gui/{uid}", agent_plist], check=True)


@main.command()
@click.argument('agent')
def bootstrap(agent, uid=UID):
    """bootstrap agent"""
    agent_plist, agent_name = get_agent(agent)
    subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", agent_plist], check=True)


@main.command()
@click.argument('agent')
def disable(agent, uid=UID):
    """disable agent"""
    agent_plist, agent_name = get_agent(agent)
    subprocess.run(["launchctl", "disable", f"gui/{uid}/{agent_name}"], check=True)


@main.command()
@click.argument('agent')
def enable(agent, uid=UID):
    """enable agent"""
    agent_plist, agent_name = get_agent(agent)
    subprocess.run(["launchctl", "enable", f"gui/{uid}/{agent_name}"], check=True)


@main.command()
def hostinfo():
    """hostinfo"""
    subprocess.run(["launchctl", "hostinfo"], check=True)


@main.command()
@click.argument('agent')
def kickstart(agent, uid=UID):
    """kickstart agent"""
    agent_plist, agent_name = get_agent(agent)
    subprocess.run(['launchctl', 'kickstart', f'gui/{uid}/{agent_name}'])


@main.command()
@click.argument('agent')
def kill(agent, uid=UID):
    """kill agent"""
    agent_plist, agent_name = get_agent(agent)
    subprocess.run(['launchctl', 'kill', 'SIGTERM', f'gui/{uid}/{agent_name}'])


@main.command(name='list')
@click.argument('agent', required=False)
def list_command(agent=None, all_agents_regex=ALL_AGENTS_REGEX):
    """list agent(s)"""
    if agent:
        agent_plist, agent_name = get_agent(agent)
        subprocess.run(['launchctl', 'list', agent_name])
    else:
        output = subprocess.run(['launchctl', 'list'], capture_output=True, text=True).stdout
        lines = output.splitlines()
        filtered_lines = [line for line in lines if
                          "PID" in line or any(agent in line for agent in all_agents_regex.split("|"))]
        sorted_lines = sorted(filtered_lines, key=lambda x: x.split()[2])
        for line in sorted_lines:
            print(line)


@main.command(name='print')
@click.argument('agent')
def print_command(agent, uid=UID):
    """print agent"""
    agent_plist, agent_name = get_agent(agent)
    subprocess.run(['launchctl', 'print', f'gui/{uid}/{agent_name}'])


@main.command()
def variant():
    """variant"""
    subprocess.run(["launchctl", "variant"], check=True)


@main.command()
def version():
    """version"""
    subprocess.run(["launchctl", "version"], check=True)
