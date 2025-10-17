__all__ = ('LazyGroup', 'ManagementRunner')

import importlib
import sys

import click

from feedbackbot import settings


class LazyGroup(click.Group):
    """
    lazy_subcommands is a map of the form:
    {command-name} -> {module-name}.{command-object-name}
    """
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
        import_path = self.lazy_subcommands[cmd_name]
        modname, cmd_object_name = import_path.rsplit('.', 1)

        mod = importlib.import_module(modname)
        cmd_object = getattr(mod, cmd_object_name)

        if not isinstance(cmd_object, click.BaseCommand):
            raise ValueError(
                f'Lazy loading of {import_path} failed by returning '
                'a non-command object'
            )
        return cmd_object


class ManagementRunner:

    def __init__(self):
        commands = getattr(settings, 'COMMANDS', {})

        @click.group(
            cls=LazyGroup,
            lazy_subcommands=commands,
            help='Root CLI command',
        )
        # @click.pass_context
        def root():
            pass
            # ctx.obj = import_string(os.environ.get('APP_MODULE'))

        self._root_group = root

        _module = sys.modules[__name__]
        setattr(_module, 'root', root)

    def run(self):
        self._root_group()
