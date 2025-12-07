"""Main CLI entry point."""

import click
from nccli import __version__
from nccli.utils.config import load_config

# Load configuration from ~/.nc_cli/config on startup
load_config()


class LazyGroup(click.Group):
    """A click Group that lazily loads commands."""

    def __init__(self, *args, lazy_subcommands=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.lazy_subcommands = lazy_subcommands or {}

    def list_commands(self, ctx):
        base = super().list_commands(ctx)
        lazy = sorted(self.lazy_subcommands.keys())
        return base + lazy

    def get_command(self, ctx, cmd_name):
        if cmd_name in self.lazy_subcommands:
            return self._lazy_load(cmd_name)
        return super().get_command(ctx, cmd_name)

    def _lazy_load(self, cmd_name):
        module_path, cmd_attr = self.lazy_subcommands[cmd_name].rsplit('.', 1)
        from importlib import import_module
        module = import_module(module_path)
        return getattr(module, cmd_attr)


@click.group(cls=LazyGroup, lazy_subcommands={
    'uploadDns': 'nccli.commands.upload_dns.upload_dns',
    'downloadDns': 'nccli.commands.download_dns.download_dns',
    'upgrade': 'nccli.commands.upgrade.upgrade',
    'config': 'nccli.commands.config_cmd.config',
    'commit': 'nccli.commands.commit.commit',
})
@click.version_option(version=__version__)
def main():
    """NC CLI - A tool for managing DNS entries."""
    pass


if __name__ == "__main__":
    main()
