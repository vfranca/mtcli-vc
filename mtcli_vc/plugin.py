from mtcli_vc.volume import volume


def register(cli):
    """Registra o comando 'vc' no CLI do mtcli."""
    cli.add_command(volume, name="vc")
