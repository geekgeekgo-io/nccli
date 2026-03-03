"""Help command showing usage examples for all commands."""

import click


HELP_TEXT = """
{title}

{summary_title}
  nccli is a CLI tool for managing the nc.local lab environment.
  It handles DNS syncing, reverse proxy setup, SSH welcome screens,
  and self-upgrading from GitHub releases.

{commands_title}

  {cmd}proxy{reset} - Set up reverse proxy, DNS, and Cloudflare tunnel
    Usage: nccli proxy <prefix> <endpoint> <mode> [options]

    Arguments:
      prefix     Domain prefix (e.g. 'myapp' for myapp.nc.local)
      endpoint   Backend URL (e.g. http://192.168.1.61:3000)
      mode       nginx | cloudflare | both

    Options:
      --proxy-server TEXT  Nginx server (default: root@192.168.1.21)
      --bind9-server TEXT  DNS server (default: root@192.168.1.11)
      --dns-ip TEXT        DNS A record IP (default: 192.168.1.21)
      --dry-run            Preview without making changes

    Examples:
      nccli proxy myapp http://192.168.1.61:3000 nginx
      nccli proxy myapp http://192.168.1.61:3000 both
      nccli proxy myapp http://192.168.1.61:3000 nginx --dry-run

  {cmd}welcome{reset} - Configure SSH login welcome screen on Ubuntu
    Usage: nccli welcome <target> [options]

    Sets up a custom MOTD (Message of the Day) on a remote Ubuntu server.
    When users SSH into the server, they see an ASCII art banner and
    system information (IP, CPU, memory, disk, load).

    Arguments:
      target     SSH destination (e.g. root@192.168.1.41)

    Options:
      --text TEXT      The ASCII art banner text shown at login.
                       This is the large figlet text displayed at the top
                       of the welcome screen (e.g. "PRDAPI01", "DEV-WEB").
                       If omitted, the server hostname is used in uppercase.
      --font TEXT      figlet font (default: slant)
                       Available: standard, slant, banner, big, block,
                       bubble, digital, lean, small
      --color TEXT     Banner color (default: cyan)
                       Options: red, green, yellow, blue, magenta, cyan, white

    Examples:
      nccli welcome root@192.168.1.41
      nccli welcome root@192.168.1.41 --text "PROD-API"
      nccli welcome root@192.168.1.41 --text "PRDAPI01" --font slant --color cyan
      nccli welcome root@192.168.1.41 --text "DEV-01" --font big --color green

    Result (example with --text "PRDAPI01"):
        ____  ____  ____  ___    ____  ________ ___
       / __ \\/ __ \\/ __ \\/   |  / __ \\/  _/ __ <  /
      / /_/ / /_/ / / / / /| | / /_/ // // / / / /
     / ____/ _, _/ /_/ / ___ |/ ____// // /_/ / /
    /_/   /_/ |_/_____/_/  |_/_/   /___/\\____/_/

      Welcome to prdapi01
      System Information:
        - IP Address: 192.168.1.33
        - CPU Cores:  4
        - Memory:     1.2Gi/4.0Gi
        ...

  {cmd}uploadDns{reset} - Upload /etc/hosts entries to MongoDB
    Usage: nccli uploadDns [--hosts-file PATH] [--database NAME] [--replace]

    Examples:
      sudo -E nccli uploadDns
      sudo -E nccli uploadDns --replace

  {cmd}downloadDns{reset} - Download DNS entries from MongoDB to /etc/hosts
    Usage: nccli downloadDns [--backup] [--dry-run]

    Examples:
      sudo -E nccli downloadDns --backup
      nccli downloadDns --dry-run

  {cmd}config{reset} - Manage nccli configuration
    Usage: nccli config [--init] [--show] [--mongodb-uri URI]

    Examples:
      nccli config --init
      nccli config --show

  {cmd}upgrade{reset} - Upgrade nccli to latest version
    Usage: nccli upgrade [--check] [--force]

    Examples:
      nccli upgrade
      nccli upgrade --check

  {cmd}version{reset} / {cmd}about{reset} - Show version and project info
    Examples:
      nccli version
      nccli about

{more_title}
  nccli <command> --help    Show detailed help for a command
  nccli help <command>      Same as above
  nccli --help              Show all available commands
"""


@click.command('help')
@click.argument('command', required=False)
def help_cmd(command):
    """Show usage examples for all commands.

    Optionally pass a COMMAND name to see help for that specific command.

    \b
    Examples:
        nccli help
        nccli help proxy
        nccli help welcome
    """
    if command:
        # Delegate to the specific command's --help
        ctx = click.get_current_context()
        main_group = ctx.parent.command if ctx.parent else None
        if main_group and hasattr(main_group, 'get_command'):
            cmd = main_group.get_command(ctx.parent, command)
            if cmd:
                # Print the command's help
                with click.Context(cmd, info_name=f"nccli {command}") as sub_ctx:
                    click.echo(cmd.get_help(sub_ctx))
                return
        click.echo(f"Unknown command: {command}")
        click.echo("Run 'nccli help' to see all commands.")
        return

    # Show full help with formatting
    output = HELP_TEXT.format(
        title=click.style("NCCLI Command Reference", fg='cyan', bold=True),
        summary_title=click.style("Summary:", fg='yellow', bold=True),
        commands_title=click.style("Commands:", fg='yellow', bold=True),
        more_title=click.style("More Info:", fg='yellow', bold=True),
        cmd="\033[1;32m",
        reset="\033[0m",
    )
    click.echo(output)
