# Fotokite API Python Examples

## Dependency Management

We use [Poetry](https://python-poetry.org/) for dependency management and packaging. Poetry makes it easy to install, update, and manage all required dependencies in a clean and consistent way.

## Makefile

To simplify running the examples, we’ve included a `Makefile` with convenient targets. You can easily run individual examples or full demo scripts using the provided commands.

This setup helps you get up and running quickly, without having to manually manage complex commands or environments.

### In Detail

- **System**
  All available actions can be found at `./fotokite_api/system/system.py`.
  Run: `make run_system action=<desired_action>`

- **Flight**
  All available actions can be found at `./fotokite_api/flight/flight.py`.
  Run: `make run_flight action=<desired_action>`

- **Notifications**
  All available actions can be found at `./fotokite_api/notifications/notifications.py`.
  Run: `make run_notifications action=<desired_action>`

- **Flight Demo**
  Run: `make run_demo_flight`

<div style="background-color:#CF8008; color:white; padding:1em; border-radius:6px;">
Important <br/>
Some of these commands will start the system.<br>
Make sure the system is in an environment where it is safe to take off if a corresponding action is triggered.
</div>
<br/>
