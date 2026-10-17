"""Pure control contracts; timestamps passed here are monotonic receipt times."""
import math
import time


def clamp(value,low,high):
    return max(low,min(high,value))


class SpeedController:
    def __init__(self,config):
        self.config=config
        self.received=None
        self.target=0.
        self.angle=0.
        self.integral=0.
        self.last=None

    def command(self,speed,yaw_rate,now):
        if not all(math.isfinite(v) for v in (speed,yaw_rate,now)) or speed<0:
            self.received=None
            self.target=self.angle=0.
            self.integral=0.
            return False
        self.target=clamp(speed,0.,self.config['max_speed'])
        self.angle=clamp(math.atan(self.config['wheelbase']*yaw_rate/speed),-self.config['max_steer'],self.config['max_steer']) if speed>=.05 else 0.
        self.received=now
        return True

    def step(self,now,speed,report_age,enabled,inhibited):
        dt=clamp(now-self.last,0.,.1) if self.last is not None else 0.
        self.last=now
        fresh=self.received is not None and 0<=now-self.received<=self.config['command_timeout']
        usable=math.isfinite(speed) and 0<=report_age<=self.config['report_timeout'] and enabled and not inhibited
        target=self.target if fresh and usable else 0.
        if not usable or not fresh or target<.01:
            self.integral=0.
            return 0.,.4,self.angle if usable else 0.,'tracking' if fresh and usable else 'inhibited'
        error=target-speed
        self.integral=clamp(self.integral+error*dt,-.3,.3)
        effort=2.*error+.4*self.integral+self.config['mock_drag']*target/self.config['mock_accel_gain']
        if effort>=0:
            return clamp(effort,0.,.65),0.,self.angle,'tracking'
        return 0.,clamp(-effort,0.,.75),self.angle,'tracking'


class MockState:
    def __init__(self):
        self.enabled=False
        self.fault=False
        self.override=False
        self.timeout=False
        self.gear=2
        self.velocity=0.
        self.angle=0.

    def enable(self,requested,ready):
        if not requested:
            self.enabled=False
            return True
        if not ready or self.fault or self.override:
            return False
        self.timeout=False
        self.enabled=True
        return True

    def trip(self,reason):
        self.enabled=False
        if reason=='fault':self.fault=True
        if reason=='override':self.override=True
        if reason=='timeout':self.timeout=True

    def shift(self,gear,speed):
        if gear not in (0,2,3) or not math.isfinite(speed):
            self.trip('fault')
            return False
        if gear!=self.gear and abs(speed)>.05:
            self.trip('fault')
            return False
        self.gear=gear
        return True

    def advance(self,dt,accel,brake,shaft,rate,ready,config):
        if not all(math.isfinite(v) for v in (dt,accel,brake,shaft,rate)) or not 0<=accel<=1 or not 0<=brake<=1 or rate<0 or abs(shaft)>config['max_steer']*config['steering_ratio']+1e-6 or (accel>.001 and brake>.001):
            self.trip('fault')
        if not ready and self.enabled:self.trip('timeout')
        if not self.enabled or self.gear!=3:
            self.velocity=0.
            return 0.,self.angle
        dt=clamp(dt,0.,.1)
        limit=min(rate,config['steering_rate'])/config['steering_ratio']
        self.angle+=clamp(shaft/config['steering_ratio']-self.angle,-limit*dt,limit*dt)
        acceleration=config['mock_accel_gain']*accel-config['mock_brake_gain']*brake-config['mock_drag']*self.velocity
        self.velocity=clamp(self.velocity+acceleration*dt,0.,config['max_speed']+.05)
        return self.velocity,self.angle


class ReadinessLease:
    """Require live advancing heartbeats; expiry requires explicit re-enable."""
    def __init__(self, timeout):
        self.timeout = timeout
        self.received = None
        self.session = None
        self.sequence = None
        self.ready = False
        self.fault_latched = False
        self.was_permitted = False

    def receive(self, session, sequence, ready, now):
        if not isinstance(session, str) or not session or type(sequence) is not int or sequence < 1 or type(ready) is not bool or not math.isfinite(now):
            return False
        if session == self.session and self.sequence is not None and sequence <= self.sequence:
            return False
        if self.session is not None and session != self.session and self.was_permitted:
            self.fault_latched = True
        self.session, self.sequence = session, sequence
        self.received, self.ready = now, ready
        return True

    def live(self, now):
        return self.received is not None and 0 <= now-self.received <= self.timeout and self.ready

    def permit(self, now):
        if not self.live(now):
            if self.was_permitted:
                self.fault_latched = True
            return False
        if self.fault_latched:
            return False
        self.was_permitted = True
        return True

    def rearm(self, now):
        if not self.live(now):
            return False
        self.fault_latched = False
        self.was_permitted = False
        return True


class CommandBundle:
    """Assemble bounded, distinct advancing ROS-stamp cycles across topics.

    Duplicate committed stamps never refresh command freshness. A frozen ROS
    clock therefore cannot renew actuation permission with repeated commands.
    """
    def __init__(self, max_pending=64, max_age=.75):
        self.pending = {}
        self.last_stamp = None
        self.max_pending = max_pending
        self.max_age = max_age

    def push(self, key, stamp, value, now=None):
        now = time.monotonic() if now is None else now
        if key not in ('accel', 'brake', 'steer') or not math.isfinite(now):
            return None
        if self.last_stamp is not None and stamp <= self.last_stamp:
            return None
        self.pending = {s:frame for s,frame in self.pending.items() if 0 <= now-frame['received'] <= self.max_age}
        frame = self.pending.setdefault(stamp, {'received':now, 'values':{}})
        if key in frame['values']:
            return None
        frame['values'][key] = value
        if all(k in frame['values'] for k in ('accel', 'brake', 'steer')):
            self.last_stamp = stamp
            result = frame['values'].copy()
            self.pending = {s:f for s,f in self.pending.items() if s > stamp}
            return result
        while len(self.pending) > self.max_pending:
            del self.pending[min(self.pending)]
        return None

    def reset(self):
        self.pending.clear()
        self.last_stamp = None
