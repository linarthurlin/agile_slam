"""Fault state shared by lifecycle callbacks and readiness publication."""


class ReadinessState:
    def __init__(self):
        self.active = False
        self.failed = False

    def trip(self):
        self.failed = True
        self.active = False

    def complete_startup(self, success):
        if self.failed:
            return False
        if not success:
            self.trip()
            return False
        self.active = True
        return True
