class PostFork:
    """
    Mock for uwsgi postfork
    """

    def __init__(self, f):
        if callable(f):
            self.f = f
        else:
            self.f = None

    def __call__(self, *args, **kwargs):
        if self.f:
            return self.f()
        self.f = args[0]
