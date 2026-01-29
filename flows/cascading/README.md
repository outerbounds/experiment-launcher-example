Example flow that uses a bunch of `Parameters` defined
in a separate module, `parameters.py`.

You can use this pattern to cleanly separate a large set
of parameters in a file of its own. A custom UI included
in this project will read the past runs of this flow
and allow you to trigger a new one through an event.
