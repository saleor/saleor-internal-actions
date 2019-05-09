import argparse

from django.core.management import (
    CommandError,
    get_commands,
    BaseCommand,
    load_command_class,
)
from django.db import connection
from tenant_schemas.management.commands.tenant_command import Command as TenantCommand
from tenant_schemas.utils import get_tenant_model


class Command(TenantCommand):
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            "-d", "--domain", dest="domain", help="specify domain name", default=None
        )

    def run_from_argv(self, argv):
        """
        Changes the option_list to use the options from the wrapped command.
        Adds schema parameter to specify which schema will be used when
        executing the wrapped command.
        """
        # load the command object.
        try:
            app_name = get_commands()[argv[2]]
        except KeyError:
            raise CommandError("Unknown command: %r" % argv[2])

        if isinstance(app_name, BaseCommand):
            # if the command is already loaded, use it directly.
            klass = app_name
        else:
            klass = load_command_class(app_name, argv[2])

        # Ugly, but works. Delete tenant_command from the argv, parse the schema manually
        # and forward the rest of the arguments to the actual command being wrapped.
        del argv[1]
        schema_parser = argparse.ArgumentParser()
        schema_parser.add_argument(
            "-d", "--domain", dest="domain", help="specify domain name"
        )
        args_namespace, args = schema_parser.parse_known_args(argv)
        tenant = self.get_tenant_from_domain(args_namespace.domain)

        connection.set_tenant(tenant)
        klass.run_from_argv(args)

    def get_tenant_from_domain(self, domain):
        TenantModel = get_tenant_model()
        try:
            return TenantModel.objects.get(domain_url=domain)
        except TenantModel.DoesNotExist:
            raise CommandError("Invalid tenant domain, %s" % domain)
