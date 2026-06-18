import faust

from simple_settings import settings
from logging.config import dictConfig

app = faust.App(
    version=1,
    autodiscover=True,
    origin='example',
    id="1",
    broker=settings.KAFKA_BOOTSTRAP_SERVER,
    logging_config=dictConfig(settings.LOGGING),
)


def main() -> None:
    app.main()


# Wire the Users CLI commands into the app's own import graph so that the real
# `faust -A example.app send-user` / `send-advance-user` entry points register
# the subcommands at import time. This makes the commands available on the
# actual CLI path (faust's find_app -> prepare_app imports this module before
# dispatching), not only when venusian autodiscovery happens to walk the
# package. Importing here is safe: `app` is already defined above, so the
# downstream `from example.app import app` in example.users.agents resolves.
import example.users.cli  # noqa: F401  (side effect: registers AppCommands)
