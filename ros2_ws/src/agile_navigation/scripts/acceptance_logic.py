"""Fresh, advancing feedback required for a consecutive rest interval."""
import math


class RestWindow:
    def __init__(self, duration=1.0, max_gap=.5, min_samples=5):
        self.duration=duration;self.max_gap=max_gap;self.min_samples=min_samples
        self.last_stamp=None;self.received=None;self.started=None;self.samples=0;self.active=False

    def start(self):
        self.active=True;self.started=None;self.samples=0

    def observe(self, stamp, speed, now):
        if not all(math.isfinite(v) for v in (stamp,speed,now)):
            self.started=None;self.samples=0
            return False
        if self.last_stamp is not None and stamp<=self.last_stamp:
            if stamp<self.last_stamp:self.last_stamp=stamp
            self.started=None;self.samples=0
            return False
        previous=self.received
        self.last_stamp=stamp;self.received=now
        if not self.active:return True
        if abs(speed)>=.02:
            self.started=None;self.samples=0
            return True
        if self.started is None or previous is None or now-previous>self.max_gap:
            self.started=now;self.samples=0
        self.samples+=1
        return True

    def ready(self, now):
        return self.started is not None and self.received is not None and 0<=now-self.received<=self.max_gap and now-self.started>=self.duration and self.samples>=self.min_samples
